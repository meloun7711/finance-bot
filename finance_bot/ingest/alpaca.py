"""
Alpaca market-data adapter — datacenter-friendly price source for cloud runs.

Yahoo's free endpoints 429 / connection-reset from cloud (datacenter) IPs, which
breaks the cloud routine. Alpaca's Market Data API is built for programmatic
access and works fine from anywhere, so it's the reliable source for FNCBOT in
the cloud. Free tier uses the IEX feed (plenty for daily bars on liquid names).

Keys are read from the environment — this module NEVER hardcodes them:
    APCA_API_KEY_ID      (or ALPACA_API_KEY_ID)
    APCA_API_SECRET_KEY  (or ALPACA_API_SECRET_KEY)
A data-only (read) key is enough; no trading scope is used or needed.

Writes the same per-ticker parquet schema as the yfinance path
(data/prices/<T>.parquet with Close/High/Low/Open/Volume/ticker, index=date),
so everything downstream (graph, profile, fncbot, backtest) is unchanged.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from finance_bot.universe import all_tickers
from finance_bot.ingest.prices import _parquet_path

BARS_URL = "https://data.alpaca.markets/v2/stocks/bars"


def _keys() -> tuple[str | None, str | None]:
    kid = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY_ID")
    sec = os.environ.get("APCA_API_SECRET_KEY") or os.environ.get("ALPACA_API_SECRET_KEY")
    return kid, sec


def _proxies() -> dict | None:
    """In a CCR cloud sandbox, egress is forced through a local proxy. `requests`
    doesn't pick it up automatically (no HTTP(S)_PROXY set), so a direct call is
    firewalled with an nginx 401. Route through the CCR proxy explicitly when it's
    present; locally (no CCR) return None for a normal direct connection."""
    for var in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        if os.environ.get(var):
            u = os.environ[var]
            return {"http": u, "https": u}
    port = os.environ.get("CLOUDSDK_PROXY_PORT")
    if port and os.environ.get("CCR_AGENT_PROXY_ENABLED"):
        u = f"http://127.0.0.1:{port}"
        return {"http": u, "https": u}
    return None


def download_alpaca(tickers: list[str] | None = None, years: float = 2.0,
                    feed: str = "iex", chunk: int = 100) -> int:
    """Fetch ~`years` of daily bars from Alpaca and write parquet per ticker.

    Returns the number of tickers written. Raises if keys are missing (so the
    routine reports a clear, actionable error instead of trading on no data).
    """
    kid, sec = _keys()
    if not kid or not sec:
        raise RuntimeError(
            "Alpaca keys missing — set APCA_API_KEY_ID and APCA_API_SECRET_KEY "
            "in the environment (data-only key is fine).")
    tickers = tickers or all_tickers()
    start = (datetime.now(timezone.utc)
             - timedelta(days=int(365 * years) + 45)).strftime("%Y-%m-%d")
    headers = {"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec}
    proxies = _proxies()
    written = 0

    for i in range(0, len(tickers), chunk):
        grp = tickers[i:i + chunk]
        collected: dict[str, list] = {t: [] for t in grp}
        page_token = None
        while True:
            params = {"symbols": ",".join(grp), "timeframe": "1Day",
                      "start": start, "limit": 10000,
                      "adjustment": "all", "feed": feed}
            if page_token:
                params["page_token"] = page_token
            try:
                r = requests.get(BARS_URL, headers=headers, params=params,
                                 timeout=30, proxies=proxies)
            except Exception as exc:
                print(f"  ! chunk {i//chunk + 1}: {type(exc).__name__}: {exc}")
                break
            if r.status_code != 200:
                print(f"  ! chunk {i//chunk + 1}: HTTP {r.status_code}: {r.text[:200]}")
                break
            payload = r.json()
            for sym, arr in (payload.get("bars") or {}).items():
                collected.setdefault(sym, []).extend(arr)
            page_token = payload.get("next_page_token")
            if not page_token:
                break

        for tk, arr in collected.items():
            if not arr:
                continue
            df = pd.DataFrame(arr)
            df["date"] = (pd.to_datetime(df["t"], utc=True)
                          .dt.tz_localize(None).dt.normalize())
            df = df.rename(columns={"o": "Open", "h": "High", "l": "Low",
                                    "c": "Close", "v": "Volume"})
            df = (df.drop_duplicates("date").set_index("date")
                  .sort_index()[["Close", "High", "Low", "Open", "Volume"]])
            df["ticker"] = tk
            df.to_parquet(_parquet_path(tk))
            written += 1
        print(f"  alpaca chunk {i//chunk + 1}: {written}/{len(tickers)} written")
    return written


if __name__ == "__main__":
    n = download_alpaca(["AAPL", "NVDA", "XOM", "LMT", "TSM"], years=1.0)
    print(f"wrote {n}")
