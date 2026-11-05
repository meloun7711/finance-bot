"""
Exit-strategy backtest — does adding a downside exit rule fix FNCBOT's biggest
weakness (losers running −12% while winners are cut at +8%)?

The base engine (backtest/portfolio.py) has NO exit rule: a name is only sold at
the next scheduled rebalance, and only if it drops out of the top-N by score. So
a position can bleed 20-30% before it's cut. This module adds position-level
exits that are checked EVERY day and, crucially, stay leak-free:

    decide at the CLOSE of day t  ->  execute at the OPEN of day t+1

Two exit rules (either/both can be on):
  * stop_loss  — hard stop on return since entry:  close/entry - 1 <= -SL
  * trail      — trailing stop from the peak close since entry: close/peak - 1 <= -TR
When a stop fires, the name is sold and BLOCKED from re-entry for `cooldown`
trading days (so we don't immediately rebuy a falling knife at the next
rebalance). Freed cash waits until the next scheduled rebalance to redeploy.

No take-profit on purpose: the diagnosed problem is cutting winners early, so we
do the opposite — cap the downside, let winners run.

Nothing here trades live. It reports what the rules WOULD have done, and logs
every realized round-trip so win-rate / avg-win / avg-loss can be compared.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from finance_bot import config
from finance_bot.backtest.portfolio import (
    score_matrix, _field_matrix, _decision_dates, _stats)
from finance_bot.universe import all_tickers

GATE = 0.33
MAX_POSITIONS = 20
POS_CAP = config.MAX_TRADE_FRACTION


@dataclass
class ExitParams:
    stop_loss: float | None = None      # e.g. 0.12 = hard stop at -12% from entry
    trail: float | None = None          # e.g. 0.15 = sell if -15% off the peak
    cooldown: int = 10                  # trading days a stopped name is blocked
    gate: float = GATE
    max_positions: int = MAX_POSITIONS
    pos_cap: float = POS_CAP
    rebalance: str = "W"
    fee_bps: float = 30.0


@dataclass
class ExitResult:
    equity: pd.Series
    trades: list                        # realized round-trips
    stats: dict
    trade_stats: dict
    params: ExitParams


def _trade_stats(trades: list) -> dict:
    if not trades:
        return {"n": 0}
    rets = np.array([t["ret"] for t in trades])
    wins = rets[rets > 0]
    losses = rets[rets <= 0]
    exp = float(rets.mean())
    return {
        "n": len(trades),
        "win_rate": round(len(wins) / len(rets), 3),
        "avg_win": round(float(wins.mean()), 4) if len(wins) else 0.0,
        "avg_loss": round(float(losses.mean()), 4) if len(losses) else 0.0,
        "expectancy": round(exp, 4),
        "worst": round(float(rets.min()), 4),
        "best": round(float(rets.max()), 4),
        "stop_exits": sum(1 for t in trades if t["why"] != "rebalance"),
        "rebalance_exits": sum(1 for t in trades if t["why"] == "rebalance"),
    }


def simulate(window, tradable, C, O, scores, p: ExitParams) -> ExitResult:
    """Position-level daily sim with next-open execution and daily exit checks.

    Vectorized on NumPy arrays indexed by (day, ticker) integer position; the
    per-day book logic stays explicit so the leak-free timing is auditable.
    """
    n = len(tradable)
    idx = {t: i for i, t in enumerate(tradable)}
    Cv = C.reindex(columns=tradable).to_numpy(float)      # (days, n)
    Ov = O.reindex(columns=tradable).to_numpy(float)
    Sv = scores.reindex(index=window, columns=tradable).to_numpy(float)
    fee = p.fee_bps / 1e4
    decisions = _decision_dates(window, p.rebalance)
    dec_mask = np.array([d in decisions for d in window])

    shares = np.zeros(n)
    entry = np.zeros(n)
    peak = np.zeros(n)
    cooldown = np.zeros(n, dtype=int)
    cash = 1.0
    pending_w = None                      # np array of target weights
    pending_why = None                    # dict ticker_idx -> reason
    eq = np.empty(len(window))
    trades = []

    for k in range(len(window)):
        o = Ov[k]; c = Cv[k]
        ovalid = ~np.isnan(o)
        # ── 1) execute yesterday's decision at today's OPEN ──────────────────
        if pending_w is not None:
            held_val = np.nansum(np.where(ovalid, shares * o, 0.0))
            val_open = held_val + cash
            tgt_val = np.where(ovalid, pending_w * val_open, shares * o)
            cur_val = np.where(ovalid, shares * o, 0.0)
            traded_notional = np.nansum(np.abs(tgt_val - cur_val))
            new_sh = shares.copy()
            with np.errstate(invalid="ignore", divide="ignore"):
                new_sh[ovalid] = tgt_val[ovalid] / o[ovalid]
            opening = (shares <= 1e-12) & (new_sh > 1e-12)
            closing = (shares > 1e-12) & (new_sh <= 1e-12)
            entry[opening] = o[opening]
            peak[opening] = o[opening]
            for i in np.where(closing)[0]:
                why = (pending_why or {}).get(i, "rebalance")
                trades.append({"ticker": tradable[i], "ret": o[i] / entry[i] - 1,
                               "why": why, "date": str(pd.Timestamp(window[k]).date())})
            entry[closing] = 0.0; peak[closing] = 0.0
            shares = new_sh
            cash = val_open - np.nansum(np.where(ovalid, shares * o, 0.0)) - traded_notional * fee
            pending_w = None; pending_why = None

        # ── 2) mark to close, update peaks, decrement cooldowns ──────────────
        held = shares > 1e-12
        upd = held & (~np.isnan(c)) & (c > peak)
        peak[upd] = c[upd]
        cooldown[cooldown > 0] -= 1
        eq[k] = np.nansum(np.where(~np.isnan(c), shares * c, 0.0)) + cash

        # ── 3) decide at close -> fires next open ────────────────────────────
        cvalid = ~np.isnan(c)
        r_entry = np.where(held & cvalid & (entry > 0), c / np.where(entry > 0, entry, 1) - 1, 0.0)
        r_peak = np.where(held & cvalid & (peak > 0), c / np.where(peak > 0, peak, 1) - 1, 0.0)
        forced = np.zeros(n, dtype=bool)
        why_map = {}
        if p.stop_loss is not None:
            sl = held & cvalid & (r_entry <= -p.stop_loss)
            forced |= sl
            for i in np.where(sl)[0]:
                why_map[i] = "stop_loss"
        if p.trail is not None:
            tr = held & cvalid & (r_peak <= -p.trail) & (~forced)
            forced |= tr
            for i in np.where(tr)[0]:
                why_map[i] = "trail"
        cooldown[forced] = p.cooldown

        if forced.any() or dec_mask[k]:
            weights = np.zeros(n)
            if dec_mask[k]:
                s = Sv[k]
                blocked = (cooldown > 0) | forced
                order = np.argsort(-np.where(np.isnan(s), -np.inf, s))
                picks = []
                for i in order:
                    si = s[i]
                    if np.isnan(si) or si < p.gate:
                        break
                    if blocked[i]:
                        continue
                    picks.append(i)
                    if len(picks) >= p.max_positions:
                        break
                weights[picks] = p.pos_cap
                pickset = set(picks)
                for i in np.where(held)[0]:
                    if i not in pickset and not forced[i]:
                        why_map.setdefault(i, "rebalance")
            else:
                keep = held & (~forced)
                weights[keep] = p.pos_cap
            pending_w = weights
            pending_why = why_map

    equity = pd.Series(eq, index=window)
    return ExitResult(equity=equity, trades=trades, stats=_stats(equity),
                      trade_stats=_trade_stats(trades), params=p)


def _prep(years: float):
    allt = all_tickers(include_benchmarks=True)
    C = _field_matrix("Close", allt).ffill()
    O = _field_matrix("Open", allt).ffill()
    bench_only = set(all_tickers()) - set(all_tickers(include_benchmarks=False))
    tradable = [c for c in C.columns if c not in bench_only]
    scores = score_matrix(C[tradable])
    dates = C.index
    start = max(252, len(dates) - int(round(252 * years)))
    window = dates[start:]
    Cw, Ow = C.reindex(window)[tradable], O.reindex(window)[tradable]
    spy = C.reindex(window)["SPY"]
    return window, tradable, Cw, Ow, scores, spy


def run(years: float = 6.0, p: ExitParams | None = None) -> ExitResult:
    p = p or ExitParams()
    window, tradable, Cw, Ow, scores, _ = _prep(years)
    return simulate(window, tradable, Cw, Ow, scores, p)
