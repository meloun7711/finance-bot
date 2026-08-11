"""
Portfolio walk-forward backtest — realistic edition.

Answers the honest question: does the mind's SIGNAL add anything, once you strip
out the survivorship-biased universe and charge real trading frictions?

Design (all point-in-time; no lookahead — decide at close t, TRADE AT OPEN t+1):
  * Signals: the same structural components as analyze/profile.py, vectorized as
    backward-looking rolling functions (score at t uses only closes <= t).
  * Rebalance on a schedule (daily / weekly / monthly), not every day.
  * Execution: weights decided at the close of a rebalance day are executed at
    the NEXT day's OPEN. Between rebalances, holdings drift with price (no free
    intra-period rebalancing).
  * Costs: a bps fee charged on the traded notional at every rebalance.

Three tracks, compared on identical machinery, costs, and execution:
  * strategy    — top-N by score, >= UP_GATE, equal-weight at the 5% cap
  * ew_universe — EQUAL-WEIGHT THE WHOLE UNIVERSE (zero skill). THIS is the
    honest benchmark: it carries the same survivorship bias as the strategy, so
    beating it is the only evidence the *signal* (not the hand-picked list) works.
  * spy         — S&P 500 buy & hold, a reference only (cannot isolate skill from
    the biased universe).

Survivorship caveat: the universe (universe.py THEMES) was curated in 2026 and
contains today's winners with zero delisted losers. A true fix needs a
point-in-time index-membership history we do not have — so we do NOT claim SPY
outperformance as skill. We benchmark against ew_universe instead.

Nothing here trades. It reports what the rules WOULD have done.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from finance_bot import config
from finance_bot.ingest.prices import load_prices, load_close_matrix
from finance_bot.universe import all_tickers
from finance_bot.analyze.profile import WEIGHTS

UP_GATE = 0.33
MAX_POSITIONS = 20
POS_CAP = config.MAX_TRADE_FRACTION      # 5% per name
BENCHMARK = "SPY"


def _tanh(x, scale):
    return np.tanh(x / scale)


def score_matrix(close: pd.DataFrame) -> pd.DataFrame:
    """Point-in-time structural score per (date, ticker); all backward-looking."""
    logp = np.log(close)
    logret = logp.diff()
    slope = (logp - logp.shift(200)) / 200.0
    trend = _tanh(slope * 252, 0.4)
    mom = close.shift(21) / close.shift(252) - 1.0
    momentum = _tanh(mom, 0.5)
    roll_max = close.rolling(252, min_periods=60).max()
    dd = close / roll_max - 1.0
    vol = logret.rolling(252, min_periods=60).std() * np.sqrt(252)
    stability = _tanh(-(dd.abs() * 2 + (vol - 0.4).clip(lower=0)), 1.0)
    score = (WEIGHTS["long_trend"] * trend
             + WEIGHTS["momentum"] * momentum
             + WEIGHTS["stability"] * stability).clip(-1, 1)  # news = 0 historically
    return score


def _field_matrix(field: str, tickers: list[str]) -> pd.DataFrame:
    cols = {}
    for tk in tickers:
        df = load_prices(tk)
        if df is not None and field in df.columns:
            cols[tk] = df[field]
    return pd.DataFrame(cols).sort_index()


def _decision_dates(window: pd.DatetimeIndex, freq: str) -> set:
    if freq == "D":
        return set(window)
    if freq == "W":
        key = [(d.isocalendar().year, d.isocalendar().week) for d in window]
    elif freq == "M":
        key = [(d.year, d.month) for d in window]
    else:
        raise ValueError("freq must be D, W, or M")
    df = pd.DataFrame({"d": list(window), "k": key})
    return set(df.groupby("k")["d"].max().tolist())


def _simulate(window, assets, C, O, target_fn, decision_days, fee,
              record=None, watch=None) -> pd.Series:
    """Daily equity curve with next-open execution and per-rebalance cost.

    If `record` (a list) and `watch` (a ticker) are given, append a per-day
    audit row for that ticker so the timing can be inspected: whether an
    execution fired at today's open, the shares actually held after it, and the
    target weight decided at today's close (which fires at the NEXT open).
    """
    shares = pd.Series(0.0, index=assets)
    cash = 1.0
    pending = None
    eq = []
    for d in window:
        executed = pending is not None
        if pending is not None:                      # execute at today's OPEN
            o = O.loc[d]
            valid = o.notna()
            val_open = float((shares * o)[valid].sum()) + cash
            tgt = pending.reindex(assets).fillna(0.0) * val_open
            cur = (shares * o).reindex(assets).fillna(0.0)
            traded = (tgt - cur).where(valid, 0.0)
            cost = float(traded.abs().sum()) * fee
            new_shares = shares.copy()
            new_shares[valid] = tgt[valid] / o[valid]
            shares = new_shares.fillna(0.0)
            cash = val_open - float(tgt[valid].sum()) - cost
            pending = None
        c = C.loc[d]                                 # mark to close
        eq.append(float((shares * c)[c.notna()].sum()) + cash)
        if d in decision_days:                        # decide -> execute next open
            pending = target_fn(d)
        if record is not None and watch is not None:
            record.append({
                "date": str(pd.Timestamp(d).date()),
                "executed_at_open": executed,
                "shares_held_after_open": round(float(shares.get(watch, 0.0)), 6),
                "target_decided_at_close": round(
                    float(pending.get(watch, 0.0)) if pending is not None else 0.0, 4),
            })
    return pd.Series(eq, index=window)


@dataclass
class Result:
    strat: pd.Series
    ew: pd.Series
    spy: pd.Series
    stats: dict


def _stats(eq: pd.Series) -> dict:
    r = eq.pct_change().dropna()
    n = len(r)
    total = float(eq.iloc[-1] / eq.iloc[0] - 1)
    cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (252 / max(n, 1)) - 1)
    vol = float(r.std(ddof=0) * np.sqrt(252))
    sharpe = float(np.sqrt(252) * r.mean() / r.std(ddof=0)) if r.std(ddof=0) else 0.0
    mdd = float((eq / eq.cummax() - 1).min())
    return {"total_return": round(total, 4), "cagr": round(cagr, 4),
            "vol": round(vol, 4), "sharpe": round(sharpe, 3),
            "max_drawdown": round(mdd, 4)}


def run(years: float = 3.0, rebalance: str = "W", fee_bps: float = 30.0) -> Result:
    fee = fee_bps / 1e4
    allt = all_tickers(include_benchmarks=True)
    C = _field_matrix("Close", allt).ffill()
    O = _field_matrix("Open", allt).ffill()
    if BENCHMARK not in C.columns:
        raise RuntimeError("SPY not downloaded — run Step 1 first.")

    bench_only = set(all_tickers()) - set(all_tickers(include_benchmarks=False))
    tradable = [c for c in C.columns if c not in bench_only]
    scores = score_matrix(C[tradable])

    dates = C.index
    start = max(252, len(dates) - int(round(252 * years)))
    window = dates[start:]
    decisions = _decision_dates(window, rebalance)

    Cw, Ow = C.reindex(window)[tradable], O.reindex(window)[tradable]

    def strat_target(d):
        s = scores.loc[d].dropna()
        s = s[s >= UP_GATE].sort_values(ascending=False).head(MAX_POSITIONS)
        w = pd.Series(0.0, index=tradable)
        if len(s):
            w[s.index] = POS_CAP
        return w

    def ew_target(d):
        avail = Cw.loc[d].dropna().index
        w = pd.Series(0.0, index=tradable)
        if len(avail):
            w[avail] = 1.0 / len(avail)
        return w

    strat = _simulate(window, tradable, Cw, Ow, strat_target, decisions, fee)
    ew = _simulate(window, tradable, Cw, Ow, ew_target, decisions, fee)

    spy_c = C.reindex(window)[BENCHMARK]
    spy = spy_c / spy_c.iloc[0]

    stats = {
        "strategy": _stats(strat), "ew_universe": _stats(ew), "spy": _stats(spy),
        "start": str(window[0].date()), "end": str(window[-1].date()),
        "rebalance": rebalance, "fee_bps": fee_bps,
        "excess_vs_ew": round(float(strat.iloc[-1] - ew.iloc[-1]), 4),
    }
    return Result(strat=strat, ew=ew, spy=spy, stats=stats)


if __name__ == "__main__":
    res = run(3.0, "W", 30.0)
    st = res.stats
    print(f"Walk-forward {st['start']} -> {st['end']} | rebalance={st['rebalance']} "
          f"| cost={st['fee_bps']}bps | next-open execution\n")
    print(f"{'':14}{'STRATEGY':>11}{'EW-UNIV':>11}{'SPY':>11}")
    for k in ["total_return", "cagr", "vol", "sharpe", "max_drawdown"]:
        fmt = (lambda x: f"{x:.2f}") if k == "sharpe" else (lambda x: f"{x*100:.1f}%")
        a, b, c = st["strategy"][k], st["ew_universe"][k], st["spy"][k]
        print(f"{k:14}{fmt(a):>11}{fmt(b):>11}{fmt(c):>11}")
    verdict = ("BEATS" if st["strategy"]["sharpe"] > st["ew_universe"]["sharpe"]
               else "does NOT beat")
    print(f"\nSignal {verdict} equal-weight universe on Sharpe "
          f"({st['strategy']['sharpe']} vs {st['ew_universe']['sharpe']}).")
