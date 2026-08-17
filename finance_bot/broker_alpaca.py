"""
Alpaca PAPER trading — places the target book as orders in Alpaca's paper
sandbox (virtual money). HARD-LOCKED TO PAPER: the endpoint is hardcoded to
paper-api.alpaca.markets and every call asserts it, so there is NO code path to
the live/real-money endpoint. If you somehow point it elsewhere it refuses.

No real funds, no real assets — this is a simulator, the same category as the
in-code paper engine, just executed through Alpaca so you can log in and see it.

Reconciliation each run:
  * target book = top-N names scoring >= gate, equal-weight at the 5% cap x exposure
  * close any held name not in the target
  * buy/sell (notional, fractional, market) to move each target name to its weight
"""

from __future__ import annotations

import os
import time

import requests

# ── PAPER ONLY. Do not change this to the live host. Guarded below. ──────────
BASE = "https://paper-api.alpaca.markets"
assert "paper-api" in BASE, "FNCBOT is paper-only; refusing a non-paper endpoint"

PER_NAME_CAP = 0.05
MIN_ORDER_USD = 2.0            # skip dust rebalances


def _keys():
    kid = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY_ID")
    sec = os.environ.get("APCA_API_SECRET_KEY") or os.environ.get("ALPACA_API_SECRET_KEY")
    if not kid or not sec:
        raise RuntimeError("Alpaca keys missing (APCA_API_KEY_ID / APCA_API_SECRET_KEY)")
    return kid, sec


def _proxies():
    for v in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        if os.environ.get(v):
            return {"http": os.environ[v], "https": os.environ[v]}
    port = os.environ.get("CLOUDSDK_PROXY_PORT")
    if port and os.environ.get("CCR_AGENT_PROXY_ENABLED"):
        u = f"http://127.0.0.1:{port}"
        return {"http": u, "https": u}
    return None


def _req(method: str, path: str, **kw):
    assert "paper-api" in BASE, "paper-only guard"
    kid, sec = _keys()
    h = {"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec}
    r = requests.request(method, BASE + path, headers=h, timeout=30,
                         proxies=_proxies(), **kw)
    return r


def account() -> dict:
    r = _req("GET", "/v2/account")
    r.raise_for_status()
    return r.json()


def positions() -> list[dict]:
    r = _req("GET", "/v2/positions")
    r.raise_for_status()
    return r.json()


def _order(symbol: str, notional: float, side: str) -> dict:
    body = {"symbol": symbol, "notional": round(notional, 2), "side": side,
            "type": "market", "time_in_force": "day"}
    r = _req("POST", "/v2/orders", json=body)
    if r.status_code >= 300:
        return {"symbol": symbol, "side": side, "error": r.text[:160]}
    j = r.json()
    return {"symbol": symbol, "side": side, "notional": body["notional"], "id": j.get("id")}


def _close(symbol: str) -> dict:
    r = _req("DELETE", f"/v2/positions/{symbol}")
    return {"symbol": symbol, "side": "close", "status": r.status_code}


def rebalance(targets: dict[str, float]) -> dict:
    """Move the paper account toward `targets` (symbol -> weight). Returns a summary."""
    acct = account()
    if acct.get("trading_blocked") or acct.get("account_blocked"):
        return {"error": "account blocked", "account": acct.get("status")}
    equity = float(acct["equity"])
    held = {p["symbol"]: float(p["market_value"]) for p in positions()}
    tgt_usd = {s: min(w, PER_NAME_CAP) * equity for s, w in targets.items() if w > 0}

    orders = []
    # 1) exit names no longer in the target book
    for sym in list(held):
        if sym not in tgt_usd:
            orders.append(_close(sym))
            time.sleep(0.15)
    # 2) adjust target names to their weight
    for sym, want in tgt_usd.items():
        have = held.get(sym, 0.0)
        delta = want - have
        if abs(delta) < MIN_ORDER_USD:
            continue
        orders.append(_order(sym, abs(delta), "buy" if delta > 0 else "sell"))
        time.sleep(0.15)

    errs = [o for o in orders if "error" in o]
    return {"endpoint": "PAPER", "equity": round(equity, 2),
            "targets": len(tgt_usd), "orders_sent": len(orders),
            "errors": len(errs), "error_samples": errs[:3]}


if __name__ == "__main__":
    import json
    print(json.dumps(account(), indent=2)[:400])
