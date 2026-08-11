"""
Daily driver — nudge the long-term index up or down from each day's metrics.

Step 5 (`profile.py`) computes a *structural* index from scratch: a slow,
point-in-time blend of trend / momentum / stability / news. That is the anchor.

This module adds the *fast* layer the brief asks for: "every day, based on the
metrics, add or subtract from the index." Each trading day we read that day's
signals for every name and move a running ``live_index`` a little:

    live = clip( prev  +  event_delta  -  REVERT * (prev - structural) , -1, +1)

    event_delta : today's signed metric nudge (bounded by DAY_CAP)
    REVERT      : a gentle daily pull back toward the structural anchor, so a
                  run of noisy days can't permanently corrupt the long-term
                  thesis — if the news/tape goes quiet, live decays to structural.

Every metric that contributes is logged with its own signed value, so any day's
move is fully explainable (data/profiles/_daily_log.csv).

Point-in-time safe: only bars with date <= as_of are ever read. Nothing here
places a trade — it updates a number a human reads.
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
from finance_bot.analyze.profile import (
    _squash, _news_tilt, long_term_index)

# --- daily-driver tuning (edit to taste) ---------------------------------
# How much each daily metric can push the index in one day. The index lives
# in [-1, 1]; these are deliberately small so one day never dominates.
DAILY_WEIGHTS = {
    "day_move":    0.035,   # today's return, volatility-adjusted & volume-confirmed
    "gap_shock":   0.015,   # large overnight gap (surprise)
    "range_break": 0.020,   # fresh 52-week high (+) or low (-)
    "trend_shift": 0.020,   # 50d-vs-200d posture crossing / widening
    "news_tilt":   0.030,   # same-day corroborated news (wired; 0 until Step 3)
}
DAY_CAP = 0.06        # hard cap on |event_delta| in a single day
REVERT = 0.04         # daily fraction pulled back toward the structural anchor

STATE_PATH = config.PROFILE_DIR / "_daily_state.json"
LOG_PATH = config.PROFILE_DIR / "_daily_log.csv"


# ---------------------------------------------------------------------------
# daily metric signals — each returns a value in roughly [-1, 1]
# ---------------------------------------------------------------------------
def _daily_signals(df: pd.DataFrame, ticker: str,
                   events: list[dict], as_of: pd.Timestamp) -> dict[str, float]:
    close = df["Close"].dropna()
    close = close[close.index <= as_of]
    if len(close) < 30:
        return {k: 0.0 for k in DAILY_WEIGHTS}
    logret = np.log(close / close.shift(1)).dropna()

    # 1) today's move, standardized by trailing 20d vol
    today = float(logret.iloc[-1])
    vol20 = float(logret.iloc[-21:-1].std(ddof=0)) or float(logret.std(ddof=0)) or 1e-9
    z = today / vol20
    day_move = _squash(z, scale=2.0)
    # volume confirmation: a move on heavy volume counts for more
    if "Volume" in df and df["Volume"].notna().any():
        vol = df["Volume"].reindex(close.index).dropna()
        if len(vol) > 21:
            avg = float(vol.iloc[-21:-1].mean()) or float(vol.mean())
            volmult = float(vol.iloc[-1]) / (avg or 1.0)
            day_move *= float(np.clip(volmult, 0.5, 2.0))  # 0.5x .. 2x amplification
    day_move = float(np.clip(day_move, -1.5, 1.5))

    # 2) overnight gap shock (open vs prior close), vol-adjusted
    gap_shock = 0.0
    if "Open" in df:
        op = df["Open"].reindex(close.index).dropna()
        if len(op) >= 2 and op.index[-1] == close.index[-1]:
            gap = np.log(float(op.iloc[-1]) / float(close.iloc[-2]))
            gap_shock = _squash(gap / vol20, scale=2.5)

    # 3) fresh 52-week range break
    win = close.tail(252)
    hi, lo, px = float(win.max()), float(win.min()), float(close.iloc[-1])
    if px >= hi * 0.999:
        range_break = 1.0
    elif px <= lo * 1.001:
        range_break = -1.0
    else:
        range_break = 0.0

    # 4) trend posture: where 50d sits vs 200d (structural health, changes slowly)
    if len(close) >= 200:
        ma50, ma200 = float(close.tail(50).mean()), float(close.tail(200).mean())
        trend_shift = _squash(ma50 / ma200 - 1.0, scale=0.08)
    else:
        trend_shift = 0.0

    # 5) same-day corroborated news flow (reuses the credibility-weighted tilt)
    news_tilt = _news_tilt(ticker, events, as_of)

    return {"day_move": day_move, "gap_shock": gap_shock,
            "range_break": range_break, "trend_shift": trend_shift,
            "news_tilt": news_tilt}


def _bucket(score: float) -> tuple[int, str]:
    if score >= config.LONG_TERM_UP:
        return 1, "very likely UP (long term)"
    if score <= config.LONG_TERM_DOWN:
        return -1, "likely DOWN (long term)"
    return 0, "can't tell (~0)"


def _load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


# ---------------------------------------------------------------------------
# the daily update
# ---------------------------------------------------------------------------
def daily_update(as_of: str | pd.Timestamp | None = None,
                 tickers: list[str] | None = None,
                 force: bool = False) -> pd.DataFrame:
    """Advance every name's live index by one trading day.

    Returns a summary frame (also persisted to _summary.csv, with the biggest
    movers surfaced by the CLI). Idempotent per (ticker, date) unless force.
    """
    tickers = tickers or all_tickers(include_benchmarks=False)
    events = load_events()
    state = _load_state()
    as_of = pd.Timestamp(as_of) if as_of is not None else None

    log_rows, summ_rows = [], []
    for tk in tickers:
        df = load_prices(tk)
        if df is None or "Close" not in df or df["Close"].dropna().empty:
            continue
        close = df["Close"].dropna()
        day = as_of if as_of is not None else close.index[-1]
        day = close.index[close.index <= day][-1]        # snap to a real bar
        day_key = str(pd.Timestamp(day).date())

        prof = long_term_index(tk, events=events, as_of=day)  # structural anchor
        if prof is None:
            continue
        structural = prof["long_term_index"]

        st = state.get(tk)
        # first time we see this name: seed live at the structural anchor
        prev = structural if st is None else float(st["live_index"])
        already = st is not None and st.get("last_date") == day_key
        if already and not force:
            live = prev
            sig = {k: 0.0 for k in DAILY_WEIGHTS}
            event_delta = 0.0
        else:
            sig = _daily_signals(df, tk, events, day)
            event_delta = float(np.clip(
                sum(DAILY_WEIGHTS[k] * sig[k] for k in DAILY_WEIGHTS),
                -DAY_CAP, DAY_CAP))
            pull = REVERT * (prev - structural)
            live = float(np.clip(prev + event_delta - pull, -1.0, 1.0))

        bucket, label = _bucket(live)
        state[tk] = {"live_index": round(live, 4),
                     "structural": round(structural, 4),
                     "last_date": day_key,
                     "last_delta": round(live - prev, 4)}

        # persist an enriched profile (keeps the structural view, adds the live one)
        prof.update({
            "structural_index": structural,
            "long_term_index": round(live, 3),   # the board reads this
            "daily_delta": round(live - prev, 4),
            "bucket": bucket, "label": label,
            "daily_signals": {k: round(v, 3) for k, v in sig.items()},
            "updated": day_key,
        })
        (config.PROFILE_DIR / f"{tk}.json").write_text(json.dumps(prof, indent=2))

        if not already or force:
            log_rows.append({"date": day_key, "ticker": tk,
                             "prev": round(prev, 4), "live": round(live, 4),
                             "delta": round(live - prev, 4),
                             "event_delta": round(event_delta, 4),
                             "structural": structural,
                             **{f"s_{k}": round(sig[k], 3) for k in DAILY_WEIGHTS}})
        summ_rows.append({"ticker": tk, "bucket": bucket, "index": round(live, 3),
                          "structural": structural,
                          "daily_delta": round(live - prev, 4),
                          "last_close": prof["last_close"],
                          "themes": ",".join(theme_of(tk))})

    STATE_PATH.write_text(json.dumps(state, indent=2))
    if log_rows:
        log_df = pd.DataFrame(log_rows)
        header = not LOG_PATH.exists()
        log_df.to_csv(LOG_PATH, mode="a", header=header, index=False)

    summ = pd.DataFrame(summ_rows).sort_values("index", ascending=False)
    summ.to_csv(config.PROFILE_DIR / "_summary.csv", index=False)
    return summ


if __name__ == "__main__":
    s = daily_update()
    print(f"Daily update: {len(s)} names.")
    movers = s.reindex(s["daily_delta"].abs().sort_values(ascending=False).index)
    print("\nBiggest movers today:")
    print(movers.head(12).to_string(index=False))
