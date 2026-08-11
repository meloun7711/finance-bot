"""
Central config: filesystem layout and shared parameters.

Kept dependency-free and import-cheap so every module can `from finance_bot
import config` without side effects.
"""

from __future__ import annotations

from pathlib import Path

# Project root = the folder that contains the `finance_bot` package.
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

PRICES_DIR = DATA / "prices"        # one parquet per ticker
NEWS_DIR = DATA / "news"            # raw + normalized news events
GRAPH_DIR = DATA / "graph"          # the "modular mind" (adjacency, edges)
BACKTEST_DIR = DATA / "backtests"   # backtest runs + reports
PROFILE_DIR = DATA / "profiles"     # per-stock profiles (Step 5)

for _d in (PRICES_DIR, NEWS_DIR, GRAPH_DIR, BACKTEST_DIR, PROFILE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Data parameters -----------------------------------------------------
HISTORY_PERIOD = "5y"       # yfinance period; "max" for furthest available
PRICE_INTERVAL = "1d"

# --- Risk / trading policy (SIGNALS ONLY — no auto-execution) ------------
# The engine never sends orders. These bound what a *suggested* trade may be.
MAX_TRADE_FRACTION = 0.05   # max 5% of balance per trade, per the brief
REQUIRE_MANUAL_CONFIRMATION = True   # hard gate; do not change to auto-fire

# --- Long-term index thresholds (Step 5) ---------------------------------
# The mind emits a score in [-1, +1]. These map it to a stance.
LONG_TERM_UP = 0.33         # >=  => "very likely up"  (+1 bucket)
LONG_TERM_DOWN = -0.33      # <=  => "likely down"     (-1 bucket)
# between the two => "can't tell" (~0)
