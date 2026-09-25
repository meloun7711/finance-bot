"""
Exit rules for the LIVE (Alpaca PAPER) path — the prototype fix for FNCBOT's
"losers run" weakness.

One rule, chosen by the cross-regime backtest sweep in backtest/exits.py:

    HARD STOP-LOSS at STOP_LOSS_PCT below entry, checked every run, then a
    COOLDOWN so the name can't be immediately rebought at the next rebalance.

No trailing stop, no take-profit (both hurt in testing). Alpaca positions already
carry `unrealized_plpc` (P&L % vs average entry), so the stop needs no extra
price history. Cooldown state persists in FNCBOT/cooldown.json so it survives
across daily runs and is committed with the rest of the bot state.

PAPER only — this just decides which names to close/skip; broker_alpaca does the
(paper) execution.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from finance_bot import config

COOLDOWN_FILE = config.ROOT / "FNCBOT" / "cooldown.json"


def _today() -> date:
    return datetime.utcnow().date()


def load_cooldown() -> dict[str, str]:
    if COOLDOWN_FILE.exists():
        try:
            return json.loads(COOLDOWN_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_cooldown(cd: dict[str, str]) -> None:
    COOLDOWN_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOLDOWN_FILE.write_text(json.dumps(cd, indent=2, sort_keys=True))


def active_blocks(cd: dict[str, str] | None = None, today: date | None = None) -> set[str]:
    """Symbols still inside their cooldown window (expired ones pruned by caller)."""
    cd = load_cooldown() if cd is None else cd
    today = today or _today()
    return {s for s, rel in cd.items() if _parse(rel) > today}


def _parse(s: str) -> date:
    return datetime.fromisoformat(s).date()


def check_stops(positions: list[dict], today: date | None = None,
                stop_pct: float | None = None,
                cooldown_days: int | None = None) -> dict:
    """Given Alpaca positions, decide stops and refresh the cooldown state.

    Returns {"to_close": [symbols hit], "blocked": {all currently-blocked
    symbols}, "cooldown": updated map}. Pure decision — does not execute.
    """
    stop_pct = config.STOP_LOSS_PCT if stop_pct is None else stop_pct
    cooldown_days = config.EXIT_COOLDOWN_DAYS if cooldown_days is None else cooldown_days
    today = today or _today()

    cd = load_cooldown()
    cd = {s: rel for s, rel in cd.items() if _parse(rel) > today}   # prune expired

    to_close = []
    for p in positions:
        try:
            plpc = float(p.get("unrealized_plpc"))
        except (TypeError, ValueError):
            continue
        if plpc <= -abs(stop_pct):
            sym = p["symbol"]
            to_close.append(sym)
            cd[sym] = (today + timedelta(days=cooldown_days)).isoformat()

    return {"to_close": to_close, "blocked": set(cd), "cooldown": cd}
