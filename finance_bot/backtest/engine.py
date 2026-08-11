"""
Step 4 — point-in-time backtest.

The cardinal rule here is NO LOOKAHEAD. Every decision made "as of" date t may
use only:
    * price data with index date <= t
    * news events with publish timestamp ts <= t
Nothing from the future leaks in. This is enforced structurally (we slice the
frames at t) rather than by convention.

Two tools:

1. event_study()
   For every news event, measure the stock's forward return at several
   horizons (+1, +3, +5, +10 trading days). This is a *forward* measurement
   from the event date — legitimate, because we're studying what happened
   AFTER the news, not peeking before the decision. It answers your core
   worry directly: the `reversal_rate` column tells you how often a stock that
   dropped on day+1 had recovered by day+5. If that rate is high, the mind
   learns NOT to panic-sell on a single red day.

2. Backtest.run()
   A walk-forward long/flat simulation with a pluggable signal function that
   only ever sees the past. Positions are capped at MAX_TRADE_FRACTION (5%),
   matching the brief. It reports return, Sharpe, and max drawdown, plus a
   comparison to buy-and-hold so you can see if the signal actually adds value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

import numpy as np
import pandas as pd

from finance_bot import config


# --------------------------------------------------------------------------
# 1) Event study — calibrates how much to trust a news reaction
# --------------------------------------------------------------------------

def _forward_returns(close: pd.Series, event_date: pd.Timestamp,
                     horizons: list[int]) -> dict[str, float]:
    """Return {h1, h3, ...} forward simple returns from the first trading day
    on/after event_date. NaN if not enough future data (end of sample)."""
    idx = close.index
    pos = idx.searchsorted(event_date)  # first bar with date >= event_date
    out: dict[str, float] = {}
    if pos >= len(idx):
        return {f"h{h}": np.nan for h in horizons}
    p0 = close.iloc[pos]
    for h in horizons:
        j = pos + h
        out[f"h{h}"] = float(close.iloc[j] / p0 - 1.0) if j < len(idx) else np.nan
    return out


def event_study(events: list[dict], close_matrix: pd.DataFrame,
                horizons: list[int] | None = None) -> pd.DataFrame:
    """
    Build a per-event forward-return table. One row per (event, ticker).
    Columns: id, ts, source, prior, ticker, h1..hN.
    """
    horizons = horizons or [1, 3, 5, 10]
    rows = []
    for ev in events:
        ts = pd.Timestamp(ev["ts"]).tz_convert("UTC").tz_localize(None)
        for tk in ev.get("tickers", []):
            if tk not in close_matrix.columns:
                continue
            fr = _forward_returns(close_matrix[tk].dropna(), ts, horizons)
            rows.append({
                "id": ev["id"], "ts": ts, "source": ev["source"],
                "prior": ev.get("prior", 0.0), "ticker": tk, **fr,
            })
    return pd.DataFrame(rows)


def reversal_stats(study: pd.DataFrame) -> dict:
    """
    The 'don't jump off a building' metric.

    Of events where the stock was DOWN at +1 day, what fraction had RECOVERED
    (>= 0 return vs event) by +5 days? A high number means single-day drops on
    news are frequently noise — so the mind should require confirmation before
    acting, not react to the first red candle.
    """
    if study.empty or "h1" not in study or "h5" not in study:
        return {"n": 0}
    down1 = study[study["h1"] < 0].dropna(subset=["h5"])
    if down1.empty:
        return {"n": 0}
    recovered = (down1["h5"] >= 0).mean()
    return {
        "n_down_day1": int(len(down1)),
        "reversal_rate_by_day5": round(float(recovered), 3),
        "median_h1": round(float(study["h1"].median()), 4),
        "median_h5": round(float(study["h5"].median()), 4),
    }


# --------------------------------------------------------------------------
# 2) Walk-forward long/flat backtest
# --------------------------------------------------------------------------

# A signal function: given history up to and including t, return a target
# weight in [0, MAX_TRADE_FRACTION] for the next bar. It receives:
#   close_hist : pd.Series of closes with index <= t (past only)
#   events_hist: list[dict] of events with ts <= t (past only)
SignalFn = Callable[[pd.Series, list[dict]], float]


@dataclass
class BacktestResult:
    ticker: str
    total_return: float
    buy_hold_return: float
    sharpe: float
    max_drawdown: float
    n_days: int
    equity_curve: pd.Series = field(repr=False, default=None)


def _sharpe(daily_ret: pd.Series, ann: int = 252) -> float:
    if daily_ret.std(ddof=0) == 0 or daily_ret.empty:
        return 0.0
    return float(np.sqrt(ann) * daily_ret.mean() / daily_ret.std(ddof=0))


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float((equity / peak - 1.0).min())


class Backtest:
    """
    Single-name long/flat walk-forward. Extend to a portfolio by running per
    ticker and combining, or by supplying a portfolio-level signal.
    """

    def __init__(self, close: pd.Series, events: list[dict],
                 max_weight: float | None = None,
                 warmup: int = 60):
        self.close = close.dropna()
        # index events by ticker-relevant, keep only those touching this name
        self.events = sorted(events, key=lambda e: e["ts"])
        self.max_weight = max_weight if max_weight is not None else config.MAX_TRADE_FRACTION
        self.warmup = warmup

    def run(self, signal: SignalFn) -> BacktestResult:
        c = self.close
        dates = c.index
        rets = c.pct_change().fillna(0.0)

        # pre-split events by date for O(1)-ish point-in-time slicing
        ev_ts = [pd.Timestamp(e["ts"]).tz_convert("UTC").tz_localize(None)
                 for e in self.events]

        weights = pd.Series(0.0, index=dates)
        for i in range(self.warmup, len(dates) - 1):
            t = dates[i]
            hist = c.iloc[: i + 1]                        # <= t, no lookahead
            k = np.searchsorted(ev_ts, t, side="right")   # events with ts <= t
            ev_hist = self.events[:k]
            w = float(signal(hist, ev_hist))
            weights.iloc[i + 1] = max(0.0, min(self.max_weight, w))

        strat_ret = weights.shift(0).fillna(0.0) * rets
        equity = (1.0 + strat_ret).cumprod()
        return BacktestResult(
            ticker=str(c.name),
            total_return=round(float(equity.iloc[-1] - 1.0), 4),
            buy_hold_return=round(float(c.iloc[-1] / c.iloc[self.warmup] - 1.0), 4),
            sharpe=round(_sharpe(strat_ret), 3),
            max_drawdown=round(_max_drawdown(equity), 4),
            n_days=len(dates) - self.warmup,
            equity_curve=equity,
        )


# --------------------------------------------------------------------------
# Reference signals (deliberately simple — real signals go in analyze/)
# --------------------------------------------------------------------------

def trend_signal(close_hist: pd.Series, events_hist: list[dict],
                 fast: int = 20, slow: int = 100) -> float:
    """Long (full 5%) when fast MA > slow MA, else flat. Pure price, no news."""
    if len(close_hist) < 100:
        return 0.0
    f = close_hist.tail(fast).mean()
    s = close_hist.tail(slow).mean()
    return config.MAX_TRADE_FRACTION if f > s else 0.0


def make_news_aware_signal(half_life: float = 5.0) -> SignalFn:
    """
    A signal that blends trend with recent *net news sentiment proxy*. Since we
    don't run an LLM here, it uses a crude proxy: recent event count weighted by
    source prior and recency. Positive news flow -> stay long; a spike of
    low-trust negative-less flow -> unchanged (we don't panic). Replace the
    proxy with a real scored-sentiment field when available.
    """
    from finance_bot.mind.credibility import recency_decay

    def sig(close_hist: pd.Series, events_hist: list[dict]) -> float:
        base = trend_signal(close_hist, events_hist)
        if not events_hist:
            return base
        t = close_hist.index[-1]
        flow = 0.0
        for e in events_hist[-50:]:
            age = (t - pd.Timestamp(e["ts"]).tz_convert("UTC").tz_localize(None)).days
            if age < 0 or age > 30:
                continue
            flow += e.get("prior", 0.3) * recency_decay(age, half_life)
        # more corroborated recent coverage -> keep/allow full weight;
        # thin coverage -> slightly de-risk. Never flips to short.
        scale = min(1.0, 0.5 + flow / 5.0)
        return round(base * scale, 4)

    return sig
