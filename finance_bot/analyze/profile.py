"""
Step 5 — per-stock profile and the long-term index.

The long-term index is a single number in [-1, +1]:
    +1  -> structurally very likely to go UP over the long horizon
     0  -> can't tell / mixed
    -1  -> structurally likely to go DOWN
This is the "+1 / ~0 / -1" scale from the brief. It is a MODEL OUTPUT, not
advice — it says nothing about whether *today* is a good entry.

How it's computed (all point-in-time-safe; uses only history up to `as_of`):
    long_trend   : sign & strength of the multi-year trend (200d slope, CAGR)
    momentum     : 6-12 month momentum, a well-documented long-horizon factor
    stability    : penalize names in deep drawdown / high volatility
    news_tilt    : recent corroborated news flow (a mild tilt, never dominant)

Each component is squashed to [-1, 1] and combined with fixed, editable
weights. The short-term view (whether to trade now) stays SEPARATE — that's
the trend/backtest signal — precisely so a weak short-term tape doesn't
contaminate the long-term thesis, and vice-versa.

Nothing here places a trade. It writes a profile you (a human) read.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from finance_bot import config
from finance_bot.ingest.prices import load_prices
from finance_bot.ingest.news import load_events
from finance_bot.universe import all_tickers, theme_of

# component weights for the long-term index (edit to taste; must be sensible,
# needn't sum to 1 — the result is clipped to [-1, 1])
WEIGHTS = {"long_trend": 0.40, "momentum": 0.30, "stability": 0.15,
           "news_tilt": 0.15}


def _squash(x: float, scale: float) -> float:
    """tanh squasher to [-1, 1]."""
    return float(np.tanh(x / scale)) if scale else 0.0


def _long_trend(close: pd.Series) -> float:
    """Slope of a 200-day linear fit on log price, normalized -> [-1,1]."""
    s = close.dropna().tail(200)
    if len(s) < 100:
        return 0.0
    y = np.log(s.values)
    x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]           # log-return per day
    return _squash(slope * 252, scale=0.4)   # ~annualized log-return


def _momentum(close: pd.Series) -> float:
    """12-1 month momentum (skip the most recent month), squashed."""
    s = close.dropna()
    if len(s) < 260:
        return 0.0
    p_now = s.iloc[-21]                       # ~1 month ago
    p_then = s.iloc[-252]                     # ~12 months ago
    mom = p_now / p_then - 1.0
    return _squash(mom, scale=0.5)


def _stability(close: pd.Series) -> float:
    """Reward low drawdown & moderate vol; returns [-1,1] (higher = calmer)."""
    s = close.dropna().tail(252)
    if len(s) < 60:
        return 0.0
    dd = float((s / s.cummax() - 1.0).min())          # <= 0
    vol = float(np.log(s / s.shift(1)).std(ddof=0) * np.sqrt(252))
    # deep drawdown or high vol -> negative contribution
    return _squash(-(abs(dd) * 2 + max(0.0, vol - 0.4)), scale=1.0)


def _news_tilt(ticker: str, events: list[dict], as_of: pd.Timestamp) -> float:
    """Mild tilt from recent corroborated coverage volume (not sentiment)."""
    from finance_bot.mind.credibility import recency_decay
    flow = 0.0
    for e in events:
        if ticker not in e.get("tickers", []):
            continue
        ts = pd.Timestamp(e["ts"]).tz_convert("UTC").tz_localize(None)
        age = (as_of - ts).days
        if 0 <= age <= 30:
            flow += e.get("prior", 0.3) * recency_decay(age, 5.0)
    # coverage presence is a weak positive prior; absence is neutral (0)
    return _squash(flow, scale=4.0)


def long_term_index(ticker: str, events: list[dict] | None = None,
                    as_of: pd.Timestamp | None = None) -> dict | None:
    """Compute the profile + long-term index for one ticker."""
    df = load_prices(ticker)
    if df is None or "Close" not in df or df.empty:
        return None
    close = df["Close"]
    if as_of is not None:
        close = close[close.index <= as_of]
    if close.dropna().empty:
        return None
    as_of = as_of or close.index[-1]
    events = events if events is not None else load_events()

    comps = {
        "long_trend": _long_trend(close),
        "momentum": _momentum(close),
        "stability": _stability(close),
        "news_tilt": _news_tilt(ticker, events, as_of),
    }
    score = float(np.clip(sum(WEIGHTS[k] * v for k, v in comps.items()), -1, 1))

    if score >= config.LONG_TERM_UP:
        bucket = +1
        label = "very likely UP (long term)"
    elif score <= config.LONG_TERM_DOWN:
        bucket = -1
        label = "likely DOWN (long term)"
    else:
        bucket = 0
        label = "can't tell (~0)"

    return {
        "ticker": ticker,
        "as_of": str(pd.Timestamp(as_of).date()),
        "themes": theme_of(ticker),
        "last_close": round(float(close.dropna().iloc[-1]), 2),
        "long_term_index": round(score, 3),
        "bucket": bucket,           # +1 / 0 / -1
        "label": label,
        "components": {k: round(v, 3) for k, v in comps.items()},
        "disclaimer": "Model output, not investment advice. Long-term "
                      "structural view only; not a trade recommendation.",
    }


def build_profiles(tickers: list[str] | None = None) -> pd.DataFrame:
    """Compute + persist profiles for the whole universe. Returns a summary."""
    tickers = tickers or all_tickers(include_benchmarks=False)
    events = load_events()
    rows = []
    for tk in tickers:
        prof = long_term_index(tk, events=events)
        if prof is None:
            continue
        (config.PROFILE_DIR / f"{tk}.json").write_text(json.dumps(prof, indent=2))
        rows.append({
            "ticker": tk, "bucket": prof["bucket"],
            "index": prof["long_term_index"], "last_close": prof["last_close"],
            "themes": ",".join(prof["themes"]),
        })
    summary = pd.DataFrame(rows).sort_values("index", ascending=False)
    summary.to_csv(config.PROFILE_DIR / "_summary.csv", index=False)
    return summary


if __name__ == "__main__":
    summ = build_profiles()
    if summ.empty:
        print("No profiles — run Step 1 (download) first.")
    else:
        n_up = (summ["bucket"] == 1).sum()
        n_flat = (summ["bucket"] == 0).sum()
        n_down = (summ["bucket"] == -1).sum()
        print(f"Profiled {len(summ)} names: +1={n_up}  ~0={n_flat}  -1={n_down}\n")
        print("Top 10 long-term (+):")
        print(summ.head(10).to_string(index=False))
        print("\nBottom 5 long-term (-):")
        print(summ.tail(5).to_string(index=False))
