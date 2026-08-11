# finance_bot — modular financial-news research & signal engine

A modular "mind" that ingests market data + news, links stocks by correlation
and lead/lag, backtests **without lookahead**, and emits a long-term
`+1 / ~0 / −1` index per stock — plus short-term, risk-capped trade *signals*.

> **This system produces signals and research only.** It never executes trades,
> never moves money, and gives no personalized investment advice. Any trade is
> reviewed and placed by **you**, a human. See [Safety](#safety-boundaries).

---

## The pipeline (matches the 5-step directorate)

| Step | Command | Module | Output |
|------|---------|--------|--------|
| 1. Download prices | `python -m finance_bot.cli download` | `ingest/prices.py` | `data/prices/*.parquet` |
| 2. Build the mind | `python -m finance_bot.cli graph` | `mind/graph.py` | `data/graph/mind.json` |
| 3. Collect news | `python -m finance_bot.cli news` | `ingest/news.py` + `mind/credibility.py` | `data/news/events.jsonl` |
| 4. Backtest | `python -m finance_bot.cli backtest --ticker PLTR` | `backtest/engine.py` | event study + walk-forward |
| 5. Profile | `python -m finance_bot.cli profile` | `analyze/profile.py` | `data/profiles/*.json` + `_summary.csv` |

Quick smoke test (small, fast):

```bash
python -m finance_bot.cli universe
python -m finance_bot.cli download --sample
python -m finance_bot.cli news --sample
python -m finance_bot.cli graph
python -m finance_bot.cli backtest --ticker PLTR
python -m finance_bot.cli profile
```

---

## Step 1 — the universe (~243 names + 14 benchmarks)

Curated in `finance_bot/universe.py`, grouped by theme so the mind has a prior
for what *should* move together. Explicitly includes what the brief asked for:
**defense/war** (LMT, RTX, NOC, GD, PLTR, KTOS, AVAV…), **AI** (NVDA, PLTR,
SMCI, ARM…), **quantum** (IONQ, RGTI, QBTS, QUBT…), **semiconductors** (32
names), plus tech, cyber, energy, rare-earth/materials, financials, healthcare,
space, and crypto-equity. 5 years of daily OHLCV (or `--period max`), split/
dividend-adjusted, one Parquet per symbol. Idempotent + rate-limited.

## Step 2 — the "modular mind" (`data/graph/mind.json`)

A graph over the universe with three edge types:
- **theme** — soft prior from shared sector buckets
- **corr** — realized return correlation (|ρ| ≥ threshold)
- **leadlag** — *directional*: name A's returns lead B's by *k* days

The lead/lag edges are what let a shock on one node propagate to the names it
tends to drag along, at the right time offset. Query with
`mind.graph.neighbors(ticker)` / `leaders_of(ticker)`.

## Step 3 — news & the "dishonest news" defense

Modular **adapters** (add a source = add one class). Shipped adapters use only
**public** feeds — per-ticker Yahoo Finance RSS and BBC world/business — and
map each item to tickers (via `$CASHTAG` + a name lexicon) and to themes
(war/oil/rare-earth keywords). Paywalled transcripts (Fox Business, WSJ) are
**not scraped**; add them as adapters with your own API key / licensed feed.

Every event carries a **source credibility prior** (`mind/credibility.py`).
An event's real influence is:

```
influence = source_prior × corroboration × recency_decay
```

so a lone sensational post barely moves the mind, while a claim confirmed by a
filing + two wires moves it a lot. This is the structural answer to *"be aware
of dishonest news."*

## Step 4 — point-in-time backtest (no lookahead)

`backtest/engine.py` enforces that every decision "as of" date *t* sees only
prices dated ≤ *t* and events with timestamp ≤ *t*.

- **`event_study()`** measures each event's forward returns (+1/+3/+5/+10d) and
  a **`reversal_rate`**: of stocks that dropped on day+1, how many had recovered
  by day+5. This directly quantifies the *"don't jump off a building when they
  say it's going down and next day it goes up"* problem — and is what teaches
  the mind to require confirmation instead of reacting to one red candle.
- **`Backtest.run()`** is a walk-forward long/flat sim with a pluggable signal,
  positions capped at **5%** of balance (`config.MAX_TRADE_FRACTION`), compared
  against buy-and-hold.

## Step 5 — profile + long-term index

`analyze/profile.py` emits, per stock, a score in **[−1, +1]** from long-term
trend, 12-1 momentum, stability (drawdown/vol), and a mild news tilt — bucketed
to **+1 / ~0 / −1**. The long-term thesis is kept **separate** from the
short-term trade signal on purpose, so a weak tape doesn't corrupt the thesis.

---

## Safety boundaries

- **No trade execution.** The engine emits signals; a human places every order.
  `config.REQUIRE_MANUAL_CONFIRMATION` is a hard gate.
- **Max 5% per trade**, enforced in code.
- **Not investment advice.** The `+1/~0/−1` index is a quantitative model output.
- **No paywall scraping / no ToS bypass.** News comes from public feeds or
  sources you license.

## Data & dependencies

Pure-Python stack already present: `pandas numpy scipy yfinance requests
matplotlib pyarrow` (no networkx/feedparser needed). Market data via Yahoo
Finance (yfinance). `data/` is git-ignored.

## Roadmap (not yet built)

- Real per-event sentiment scoring (LLM or finance model) to replace the
  coverage-volume proxy in the news-aware signal.
- Portfolio-level backtest & risk parity across correlated clusters.
- Broker adapter with a **manual-confirmation** order preview (no auto-fire).
