"""finance_bot — modular financial-news research & signal engine.

Pipeline (see README):
  1. ingest.prices   — download the ~250-ticker universe
  2. mind.graph      — build the correlation / lead-lag "modular mind"
  3. ingest.news     — pull & normalize news events (with credibility weights)
  4. backtest.engine — point-in-time backtest (no lookahead)
  5. analyze.profile — per-stock profile + long-term +1/0/-1 index

This package produces SIGNALS ONLY. It never executes trades or moves money.
"""

__version__ = "0.1.0"
