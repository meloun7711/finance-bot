"""
Paper-trading account — SIMULATED money only. NEVER places real orders.

Run twice per trading day by a scheduler:
  * phase="open"  — decide from yesterday's close, BUY/SELL at today's open (fills
                    + fees applied), rebalance to the signal's target book.
  * phase="close" — mark the book to today's close, record equity & daily P&L.

The signal is the same point-in-time structural score as the backtest
(trend/momentum/stability; news=0 for now): hold the top-N names scoring
>= UP_GATE, equal-weight at the 5% per-name cap. Leak-safe: the open-phase
decision uses only data up to the PRIOR close and fills at TODAY's open.

Fees are modeled on real 2026 US-equity costs (commission-free broker):
  * commission     : $0.00
  * SEC Section 31 : sells only, $20.60 / $1,000,000 of proceeds, round up to 1c
  * FINRA TAF      : sells only, $0.000195/share, min $0.01, cap $9.79/trade
  * slippage       : SLIPPAGE_BPS per side (paper fills miss the bid/ask spread)
Every trade's fees are logged and deducted from cash.

State lives in data/paper/. Deterministic — the LLM only orchestrates & reports.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from finance_bot import config
from finance_bot.ingest.prices import load_prices
from finance_bot.universe import all_tickers, theme_of
from finance_bot.backtest.portfolio import score_matrix, UP_GATE, MAX_POSITIONS, POS_CAP

PAPER_DIR = config.DATA / "paper"
PAPER_DIR.mkdir(parents=True, exist_ok=True)
STATE = PAPER_DIR / "account.json"
TRADES = PAPER_DIR / "trades.csv"
EQUITY = PAPER_DIR / "equity.csv"

START_CAPITAL = 100_000.0
REBALANCE_MIN_DELTA = 0.005      # ignore target changes smaller than 0.5% of book (cuts churn/fees)

# --- fee model (real 2026 US-equity costs; edit if your broker differs) -----
COMMISSION = 0.00
SEC_FEE_RATE = 20.60 / 1_000_000     # sells only, on $ proceeds
TAF_PER_SHARE = 0.000195             # sells only
TAF_MIN, TAF_MAX = 0.01, 9.79
SLIPPAGE_BPS = 1.0                   # per side


def trade_fees(side: str, shares: float, price: float) -> dict:
    """Explicit regulatory/commission fees for one fill (slippage handled in price)."""
    notional = shares * price
    commission = COMMISSION
    if side == "sell":
        sec = math.ceil(notional * SEC_FEE_RATE * 100) / 100.0        # round UP to 1c
        taf = min(TAF_MAX, max(TAF_MIN, shares * TAF_PER_SHARE))
    else:
        sec = taf = 0.0
    total = round(commission + sec + taf, 4)
    return {"commission": round(commission, 4), "sec": round(sec, 2),
            "taf": round(taf, 2), "total_fee": total}


def _fill_price(side: str, price: float) -> float:
    """Slippage: buys fill a hair higher, sells a hair lower."""
    s = SLIPPAGE_BPS / 1e4
    return price * (1 + s) if side == "buy" else price * (1 - s)


def _load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    st = {"created": datetime.now(timezone.utc).isoformat(),
          "capital": START_CAPITAL, "cash": START_CAPITAL, "positions": {},
          "last_open_date": None, "last_close_date": None,
          "totals": {"fees_paid": 0.0, "trades": 0, "realized_pnl": 0.0}}
    STATE.write_text(json.dumps(st, indent=2))
    return st


def _save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st, indent=2))


def _append_csv(path, row: dict) -> None:
    header = not path.exists()
    pd.DataFrame([row]).to_csv(path, mode="a", header=header, index=False)


def _matrices():
    tickers = all_tickers(include_benchmarks=False)
    C, O = {}, {}
    for tk in tickers:
        df = load_prices(tk)
        if df is not None and "Close" in df:
            C[tk] = df["Close"]
            if "Open" in df:
                O[tk] = df["Open"]
    C = pd.DataFrame(C).sort_index().ffill()
    O = pd.DataFrame(O).sort_index().ffill()
    return C, O


def _target_weights(C: pd.DataFrame, asof) -> pd.Series:
    """Top-N names scoring >= UP_GATE as of `asof`, equal-weight at the 5% cap."""
    scores = score_matrix(C).loc[asof].dropna()
    s = scores[scores >= UP_GATE].sort_values(ascending=False).head(MAX_POSITIONS)
    w = pd.Series(0.0, index=C.columns)
    if len(s):
        w[s.index] = POS_CAP
    return w


def _portfolio_value(st: dict, prices: pd.Series) -> float:
    val = st["cash"]
    for tk, pos in st["positions"].items():
        px = prices.get(tk)
        if px is not None and not np.isnan(px):
            val += pos["shares"] * float(px)
    return val


# ---------------------------------------------------------------------------
def phase_open() -> dict:
    """Rebalance to the signal at today's OPEN (decision from prior close)."""
    st = _load_state()
    C, O = _matrices()
    today = C.index[-1]
    prior = C.index[-2]
    day = str(pd.Timestamp(today).date())
    if st["last_open_date"] == day:
        return {"skipped": f"open already run for {day}"}

    opens = O.loc[today]
    target_w = _target_weights(C.loc[:prior], prior)         # leak-safe: <= prior close
    value = _portfolio_value(st, opens)                       # mark at today's open

    # desired dollars per name
    tgt_dollars = (target_w * value).reindex(C.columns).fillna(0.0)
    cur_shares = {tk: st["positions"].get(tk, {}).get("shares", 0.0) for tk in C.columns}
    cur_dollars = pd.Series({tk: cur_shares[tk] * float(opens.get(tk, np.nan))
                             for tk in C.columns}).fillna(0.0)
    delta = tgt_dollars - cur_dollars

    # sells first (raise cash), then buys; skip dust below the min-delta threshold
    order = list(delta[delta < 0].sort_values().index) + list(delta[delta > 0].sort_values(ascending=False).index)
    trades, fees_today = 0, 0.0
    for tk in order:
        px = float(opens.get(tk, np.nan))
        if np.isnan(px) or px <= 0:
            continue
        d = float(delta[tk])
        if abs(d) < max(REBALANCE_MIN_DELTA * value, 1.0):
            continue
        side = "buy" if d > 0 else "sell"
        fp = _fill_price(side, px)
        shares = abs(d) / fp
        if side == "sell":
            shares = min(shares, cur_shares[tk])              # can't sell more than held
            if shares <= 0:
                continue
        fee = trade_fees(side, shares, fp)
        # cash flow
        if side == "buy":
            st["cash"] -= shares * fp + fee["total_fee"]
        else:
            st["cash"] += shares * fp - fee["total_fee"]
        # position update
        pos = st["positions"].get(tk, {"shares": 0.0, "avg_cost": 0.0})
        if side == "buy":
            new_sh = pos["shares"] + shares
            pos["avg_cost"] = (pos["shares"] * pos["avg_cost"] + shares * fp) / new_sh
            pos["shares"] = new_sh
        else:
            realized = shares * (fp - pos["avg_cost"])
            st["totals"]["realized_pnl"] = round(st["totals"]["realized_pnl"] + realized, 2)
            pos["shares"] -= shares
        if pos["shares"] <= 1e-9:
            st["positions"].pop(tk, None)
        else:
            st["positions"][tk] = pos
        fees_today += fee["total_fee"]
        trades += 1
        _append_csv(TRADES, {"date": day, "phase": "open", "side": side, "ticker": tk,
                             "shares": round(shares, 6), "ref_price": round(px, 4),
                             "fill_price": round(fp, 4), **fee,
                             "cash_after": round(st["cash"], 2)})

    st["totals"]["trades"] += trades
    st["totals"]["fees_paid"] = round(st["totals"]["fees_paid"] + fees_today, 2)
    st["last_open_date"] = day
    _save_state(st)
    value_after = _portfolio_value(st, opens)
    return {"phase": "open", "date": day, "trades": trades,
            "fees_today": round(fees_today, 2), "cash": round(st["cash"], 2),
            "positions": len(st["positions"]), "portfolio_value": round(value_after, 2)}


def phase_close() -> dict:
    """Mark to today's close; record equity and daily P&L. No trading."""
    st = _load_state()
    C, _ = _matrices()
    today = C.index[-1]
    day = str(pd.Timestamp(today).date())
    closes = C.loc[today]
    equity = _portfolio_value(st, closes)

    prev_equity = st["capital"]
    if EQUITY.exists():
        prev = pd.read_csv(EQUITY)
        if len(prev):
            prev_equity = float(prev["equity"].iloc[-1])
    daily_pnl = equity - prev_equity
    cum_return = equity / st["capital"] - 1.0

    _append_csv(EQUITY, {"date": day, "phase": "close", "equity": round(equity, 2),
                         "cash": round(st["cash"], 2),
                         "positions_value": round(equity - st["cash"], 2),
                         "daily_pnl": round(daily_pnl, 2),
                         "cum_return": round(cum_return, 4),
                         "positions": len(st["positions"]),
                         "fees_paid_todate": st["totals"]["fees_paid"]})
    st["last_close_date"] = day
    _save_state(st)
    return {"phase": "close", "date": day, "equity": round(equity, 2),
            "daily_pnl": round(daily_pnl, 2), "cum_return": round(cum_return * 100, 2),
            "cash": round(st["cash"], 2), "positions": len(st["positions"]),
            "fees_paid_todate": st["totals"]["fees_paid"]}


def status() -> dict:
    st = _load_state()
    C, _ = _matrices()
    closes = C.loc[C.index[-1]]
    equity = _portfolio_value(st, closes)
    holds = sorted(st["positions"].items(),
                   key=lambda kv: -kv[1]["shares"] * float(closes.get(kv[0], 0) or 0))
    return {"equity": round(equity, 2), "cash": round(st["cash"], 2),
            "cum_return_pct": round((equity / st["capital"] - 1) * 100, 2),
            "positions": len(st["positions"]),
            "fees_paid_todate": st["totals"]["fees_paid"],
            "realized_pnl": st["totals"]["realized_pnl"],
            "top_holdings": [tk for tk, _ in holds[:10]]}


def reset(capital: float = START_CAPITAL) -> None:
    for p in (STATE, TRADES, EQUITY):
        if p.exists():
            p.unlink()
    st = _load_state()
    st["capital"] = st["cash"] = capital
    _save_state(st)
