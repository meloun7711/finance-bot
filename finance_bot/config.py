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

# --- Exit rule (prototype) ------------------------------------------------
# Diagnosed weakness: losers were left to run (worst trades −30% to −47%) while
# winners were cut. Fix, chosen by a 6-year cross-regime sweep (see
# backtest/exits.py): a single WIDE HARD STOP on return-since-entry. Tighter
# stops (8–12%) and trailing stops whipsawed out of dips that recover; −15% only
# fires on genuine breakdowns and truncates the worst trade to ~−22%. The −15% /
# 10-trading-day levels sit on a flat plateau (robust, not an overfit spike).
STOP_LOSS_PCT = 0.15          # force-close a name down >=15% from entry
EXIT_COOLDOWN_DAYS = 14       # calendar days a stopped name is blocked (~10 trading days)
NO_TRAILING_STOP = True       # documented: trailing stops hurt returns here
NO_TAKE_PROFIT = True         # documented: never cap winners (that was the disease)

# --- Long-term index thresholds (Step 5) ---------------------------------
# The mind emits a score in [-1, +1]. These map it to a stance.
LONG_TERM_UP = 0.33         # >=  => "very likely up"  (+1 bucket)
LONG_TERM_DOWN = -0.33      # <=  => "likely down"     (-1 bucket)
# between the two => "can't tell" (~0)
