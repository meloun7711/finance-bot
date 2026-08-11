"""
Screen — strong long-term thesis, weak short-term tape ("dip in an uptrend").

The brief keeps two views deliberately separate:
    * the LONG-TERM index (Step 5 / profile.py) — is this a structural winner?
    * the SHORT-TERM tape (daily driver / trend) — what is price doing now?

This module finds the divergence the user is after: names the model still
rates a long-term UP, but which are *currently pulling back*. That's the
difference between a healthy dip to lean into and a falling knife whose
long-term thesis has also broken.

A candidate must clear three gates (all point-in-time):
    1. structural_index >= UP_GATE          -> long-term thesis intact & strong
    2. currently down    (20-day return < 0, price below its 50-day average)
    3. NOT broken        (still above the 200-day average, pullback shallower
                          than MAX_PULLBACK — deeper than that and we treat the
                          trend as damaged, not a dip)

Candidates are ranked by a transparent setup score that rewards a strong
long-term thesis AND a deeper/oversold short-term dip. MODEL OUTPUT, NOT ADVICE
— this flags a pattern; it does not tell anyone to buy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_bot import config
from finance_bot.ingest.prices import load_prices
from finance_bot.ingest.news import load_events
from finance_bot.universe import all_tickers, theme_of
from finance_bot.analyze.profile import long_term_index

UP_GATE = 0.33          # long-term thesis must be at least "very likely up"
MAX_PULLBACK = -0.30    # deeper than -30% off the recent high => "broken", skip
RECENT_HIGH_WIN = 60    # window (days) for the pullback reference high


def _rsi(close: pd.Series, n: int = 14) -> float:
    d = close.diff().dropna().tail(n * 3)
    if len(d) < n:
        return 50.0
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    if dn == 0:
        return 100.0
    rs = up / dn
    return float(100 - 100 / (1 + rs))


def _short_term(close: pd.Series) -> dict | None:
    s = close.dropna()
    if len(s) < 210:
        return None
    px = float(s.iloc[-1])
    ma50 = float(s.tail(50).mean())
    ma200 = float(s.tail(200).mean())
    ret20 = px / float(s.iloc[-21]) - 1.0
    ret10 = px / float(s.iloc[-11]) - 1.0
    recent_high = float(s.tail(RECENT_HIGH_WIN).max())
    pullback = px / recent_high - 1.0                  # <= 0
    below_50 = px / ma50 - 1.0
    above_200 = px / ma200 - 1.0
    return {"px": px, "ret20": ret20, "ret10": ret10, "pullback": pullback,
            "below_50": below_50, "above_200": above_200,
            "rsi14": _rsi(s), "ma50": ma50, "ma200": ma200}


def dip_in_uptrend(tickers: list[str] | None = None) -> pd.DataFrame:
    """Return ranked 'strong long-term, weak now' candidates."""
    tickers = tickers or all_tickers(include_benchmarks=False)
    events = load_events()
    rows = []
    for tk in tickers:
        df = load_prices(tk)
        if df is None or "Close" not in df:
            continue
        prof = long_term_index(tk, events=events)
        if prof is None or prof["long_term_index"] < UP_GATE:
            continue                                    # gate 1: strong long term
        st = _short_term(df["Close"])
        if st is None:
            continue

        currently_down = st["ret20"] < 0 and st["below_50"] < 0   # gate 2
        trend_intact = st["above_200"] > 0 and st["pullback"] > MAX_PULLBACK
        if not (currently_down and trend_intact):        # gate 3: not broken
            continue

        # transparent setup score: long-term conviction x short-term dip quality
        dip_depth = float(np.clip(-st["pullback"] / 0.20, 0, 1))    # deeper dip -> higher (cap 20%)
        oversold = float(np.clip((55 - st["rsi14"]) / 30, 0, 1))    # RSI<25 -> 1
        weakness = float(np.clip(-st["ret20"] / 0.15, 0, 1))        # -15% in 20d -> 1
        st_quality = 0.45 * dip_depth + 0.30 * oversold + 0.25 * weakness
        setup = round(0.6 * prof["long_term_index"] + 0.4 * st_quality, 3)

        rows.append({
            "ticker": tk, "setup": setup,
            "long_term": prof["long_term_index"],
            "ret20": round(st["ret20"], 3), "pullback": round(st["pullback"], 3),
            "below_50d": round(st["below_50"], 3), "above_200d": round(st["above_200"], 3),
            "rsi14": round(st["rsi14"], 1), "last_close": round(st["px"], 2),
            "themes": ",".join(theme_of(tk)),
        })
    out = pd.DataFrame(rows).sort_values("setup", ascending=False)
    if not out.empty:
        out.to_csv(config.PROFILE_DIR / "_dip_candidates.csv", index=False)
    return out


if __name__ == "__main__":
    df = dip_in_uptrend()
    if df.empty:
        print("No 'dip in uptrend' candidates right now.")
    else:
        print(f"{len(df)} candidates — strong long-term, currently pulling back:\n")
        print(df.head(20).to_string(index=False))
