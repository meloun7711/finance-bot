"""
Decision engine — the "brain" the routine runs on data the box committed.

Split of duties (because the CCR routine can't fetch market data):
  * BOX (has internet): downloads prices, then `export_market()` writes a compact
    wide close matrix to market/close.parquet and pushes it to the repo.
  * ROUTINE (reads repo + can WebSearch): reads market/close.parquet, optionally
    reads news_tilt.json (theme tilts it derived from news via WebSearch), then
    `decide()` produces reports/latest.md — the ranked +1/~0/−1 board, the
    dip-in-uptrend list, and how the news tilted things — and commits it.

News tilt is deliberately BOUNDED (NEWS_WEIGHT) and per-theme, so a headline can
nudge names in a sector but never dominate the price signal. Everything is
logged with its source. MODEL OUTPUT, NOT ADVICE — suggestions for a human;
the paper bot's mechanical trades stay separate and risk-capped.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from finance_bot import config
from finance_bot.ingest.prices import load_prices
from finance_bot.universe import all_tickers, theme_of
from finance_bot.backtest.portfolio import score_matrix, UP_GATE

MARKET_DIR = config.ROOT / "market"
REPORTS_DIR = config.ROOT / "reports"
NEWS_TILT = MARKET_DIR / "news_tilt.json"
NEWS_WEIGHT = 0.15                 # max sway of a full-strength theme tilt on a name's score


def export_market() -> str:
    """Box side: dump a compact wide close matrix for the routine to read."""
    MARKET_DIR.mkdir(exist_ok=True)
    cols = {}
    for tk in all_tickers(include_benchmarks=True):
        df = load_prices(tk)
        if df is not None and "Close" in df:
            cols[tk] = df["Close"].tail(520)     # ~2y is plenty for the signals
    C = pd.DataFrame(cols).sort_index()
    C.to_parquet(MARKET_DIR / "close.parquet")
    (MARKET_DIR / "meta.json").write_text(json.dumps({
        "as_of": str(C.index[-1].date()), "tickers": int(C.shape[1]),
        "rows": int(C.shape[0]), "exported": datetime.now(timezone.utc).isoformat()}))
    return f"exported market/close.parquet — {C.shape[1]} tickers through {C.index[-1].date()}"


def _load_news_tilt() -> dict:
    if NEWS_TILT.exists():
        try:
            return json.loads(NEWS_TILT.read_text())
        except Exception:
            return {}
    return {}


def decide() -> str:
    """Routine side: read committed data (+ news tilt) and write the decision report."""
    if not (MARKET_DIR / "close.parquet").exists():
        return "no market/close.parquet — the box must export it first"
    C = pd.read_parquet(MARKET_DIR / "close.parquet")
    bench = set(all_tickers()) - set(all_tickers(include_benchmarks=False))
    tradable = [c for c in C.columns if c not in bench]

    scores = score_matrix(C[tradable]).iloc[-1].dropna()        # structural, latest day
    news = _load_news_tilt()
    themes = news.get("themes", {}) if isinstance(news, dict) else {}

    def adj(tk, s):
        tl = max((float(themes.get(t, 0.0)) for t in theme_of(tk)), default=0.0)
        return float(np.clip(s + NEWS_WEIGHT * tl, -1, 1)), tl

    rows = []
    for tk, s in scores.items():
        a, tl = adj(tk, float(s))
        rows.append((tk, float(s), a, tl, ",".join(theme_of(tk))))
    df = pd.DataFrame(rows, columns=["ticker", "structural", "decision", "news_tilt", "themes"])
    df = df.sort_values("decision", ascending=False)

    # dip-in-uptrend from the matrix (strong long-term, currently pulling back)
    dips = []
    for tk in df[df.decision >= UP_GATE].ticker:
        p = C[tk].dropna()
        if len(p) < 210:
            continue
        px, ma50, ma200 = p.iloc[-1], p.tail(50).mean(), p.tail(200).mean()
        ret20 = px / p.iloc[-21] - 1
        pull = px / p.tail(60).max() - 1
        if ret20 < 0 and px < ma50 and px > ma200 and pull > -0.30:
            dips.append((tk, round(float(ret20), 3), round(float(pull), 3)))

    asof = str(C.index[-1].date())
    ev = news.get("events", []) if isinstance(news, dict) else []
    L = []
    L.append(f"# FNCBOT Decisions — {asof}\n")
    L.append(f"_Model output, not advice. Data through {asof}; {len(tradable)} names. "
             f"Paper/research signals for review — not auto-executed._\n")
    if themes:
        L.append("## News tilt (from headlines, bounded)")
        for t, v in sorted(themes.items(), key=lambda x: -abs(x[1])):
            L.append(f"- **{t}**: {v:+.2f}")
        if ev:
            L.append("\n**Events driving the tilt:**")
            for e in ev[:8]:
                L.append(f"- {e.get('headline','?')} "
                         f"→ _{', '.join(e.get('themes',[]))}_ ({e.get('source','?')})")
        L.append("")
    L.append("## Top 15 — likely UP (news-adjusted)")
    L.append("| # | Ticker | Decision | Structural | News | Themes |")
    L.append("|---|--------|---------:|-----------:|-----:|--------|")
    for i, r in enumerate(df.head(15).itertuples(), 1):
        L.append(f"| {i} | **{r.ticker}** | {r.decision:+.2f} | {r.structural:+.2f} | "
                 f"{r.news_tilt:+.2f} | {r.themes} |")
    L.append("\n## Bottom 8 — likely DOWN")
    for r in df.tail(8)[::-1].itertuples():
        L.append(f"- {r.ticker} {r.decision:+.2f} ({r.themes})")
    L.append("\n## Dip-in-uptrend (strong long-term, pulling back now)")
    if dips:
        for tk, ret20, pull in sorted(dips, key=lambda x: x[1])[:12]:
            L.append(f"- **{tk}** — 20d {ret20:+.1%}, {pull:+.1%} off recent high")
    else:
        L.append("- none today")
    report = "\n".join(L) + "\n"

    REPORTS_DIR.mkdir(exist_ok=True)
    (REPORTS_DIR / f"{asof}.md").write_text(report)
    (REPORTS_DIR / "latest.md").write_text(report)
    df.to_csv(REPORTS_DIR / f"{asof}_scores.csv", index=False)
    return f"wrote reports/latest.md — {len(tradable)} names, {len(dips)} dip candidates, news themes: {list(themes)}"


if __name__ == "__main__":
    print(export_market())
    print(decide())
