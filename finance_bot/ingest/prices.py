"""
Step 1 — download historical OHLCV for the whole universe.

Design notes
------------
* One Parquet file per ticker (data/prices/<TICKER>.parquet). This keeps each
  symbol independently refreshable and lets the backtester memory-map only
  what it needs.
* `auto_adjust=True` -> prices are split/dividend adjusted, which is what you
  want for return series. We ALSO keep raw close so the backtest can reason
  about real tradable prices if needed later.
* Idempotent: re-running only re-fetches tickers that are missing or stale,
  unless force=True.
* Batched + polite: yfinance is rate-limited by Yahoo; we chunk requests and
  retry with backoff rather than hammering.

This module downloads *prices only*. News ingestion is Step 3 (ingest/news.py).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

from finance_bot import config
from finance_bot.universe import all_tickers


def _parquet_path(ticker: str):
    return config.PRICES_DIR / f"{ticker.replace('.', '-')}.parquet"


def _is_fresh(ticker: str, max_age_days: int = 1) -> bool:
    """True if we already have a recent file for this ticker."""
    p = _parquet_path(ticker)
    if not p.exists():
        return False
    age = (datetime.now(timezone.utc)
           - datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc))
    return age.days < max_age_days


def _normalize(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Flatten yfinance output to a tidy single-ticker frame."""
    if isinstance(df.columns, pd.MultiIndex):
        # yf.download with one ticker still returns a MultiIndex sometimes.
        df = df.xs(ticker, axis=1, level=1) if ticker in df.columns.get_level_values(1) else df.droplevel(1, axis=1)
    df = df.rename(columns=str).copy()
    df.index.name = "date"
    df["ticker"] = ticker
    return df


def download_one(ticker: str, period: str | None = None,
                 interval: str | None = None) -> pd.DataFrame | None:
    """Download a single ticker; return the frame or None on failure."""
    period = period or config.HISTORY_PERIOD
    interval = interval or config.PRICE_INTERVAL
    try:
        raw = yf.download(ticker, period=period, interval=interval,
                          auto_adjust=True, progress=False, threads=False)
    except Exception as exc:  # network / parsing / rate limit
        print(f"  ! {ticker}: {type(exc).__name__}: {exc}")
        return None
    if raw is None or raw.empty:
        print(f"  ! {ticker}: no data returned")
        return None
    df = _normalize(raw, ticker)
    df.to_parquet(_parquet_path(ticker))
    return df


def download_universe(tickers: list[str] | None = None,
                      period: str | None = None,
                      force: bool = False,
                      pause: float = 0.4,
                      max_retries: int = 3) -> dict[str, str]:
    """
    Download every ticker in the universe (or a supplied subset).

    Returns a status map {ticker: "ok" | "cached" | "failed"}.
    Never raises for a single-ticker failure — it records and moves on, so a
    handful of dead symbols can't abort the whole run.
    """
    tickers = tickers or all_tickers()
    status: dict[str, str] = {}
    total = len(tickers)

    for i, tk in enumerate(tickers, 1):
        if not force and _is_fresh(tk):
            status[tk] = "cached"
            continue

        ok = False
        for attempt in range(1, max_retries + 1):
            df = download_one(tk, period=period)
            if df is not None and not df.empty:
                ok = True
                print(f"  [{i:3d}/{total}] {tk:6} {len(df):5d} rows  "
                      f"{df.index.min().date()} -> {df.index.max().date()}")
                break
            time.sleep(pause * attempt)  # backoff
        status[tk] = "ok" if ok else "failed"
        time.sleep(pause)

    ok_n = sum(v in ("ok", "cached") for v in status.values())
    print(f"\nDone: {ok_n}/{total} available "
          f"({sum(v=='failed' for v in status.values())} failed)")
    return status


def load_prices(ticker: str) -> pd.DataFrame | None:
    """Read a previously-downloaded ticker back from disk."""
    p = _parquet_path(ticker)
    return pd.read_parquet(p) if p.exists() else None


def load_close_matrix(tickers: list[str] | None = None) -> pd.DataFrame:
    """
    Wide matrix of adjusted closes: index=date, columns=ticker.
    This is the primary input to the correlation graph (Step 2) and the
    backtester (Step 4).
    """
    tickers = tickers or all_tickers()
    series = {}
    for tk in tickers:
        df = load_prices(tk)
        if df is not None and "Close" in df.columns:
            series[tk] = df["Close"]
    if not series:
        return pd.DataFrame()
    return pd.DataFrame(series).sort_index()
