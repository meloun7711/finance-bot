"""
FNCBOT — one-call-a-day self-adapting PAPER trader with version control.

Runs ONCE per trading day (~09:30 ET). Each call:
  1. SETTLE   — mark the book to the prior session's close, record equity & P&L.
  2. LEARN    — every LEARN_EVERY sessions, evaluate the live model version and
                (within hard bounds) adjust ONE knob, or REVERT the last change
                if it hurt performance. Every change is versioned & logged.
  3. TRADE    — rebalance to the signal's target book, filling at TODAY's open
                (leak-safe: the decision uses only data up to the prior close).

"Self-learning" here = a transparent, bounded, reversible controller — NOT a
black box. It adapts exposure to its own drawdown and rolls back changes that
underperform their parent version. It is NOT guaranteed to improve returns;
adapting to your own P&L can curve-fit. The whole point of the version log is so
a human can SEE whether a change helped or hurt, and roll back.

Everything lives under ./FNCBOT/. PAPER ONLY — never a real order, never funds.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from finance_bot import config
from finance_bot.ingest.prices import load_prices
from finance_bot.universe import all_tickers
from finance_bot.backtest.portfolio import score_matrix
from finance_bot.paper import trade_fees, _fill_price     # reuse the fee model

# --- home ------------------------------------------------------------------
HOME = config.ROOT / "FNCBOT"
VERSIONS = HOME / "versions"
STATE = HOME / "account.json"
MODEL = HOME / "model.json"
CHANGELOG = HOME / "changelog.jsonl"
PERF = HOME / "performance.csv"
TRADES = HOME / "trades.csv"
for _d in (HOME, VERSIONS):
    _d.mkdir(parents=True, exist_ok=True)

START_CAPITAL = 100_000.0
PER_NAME_CAP = config.MAX_TRADE_FRACTION      # 5% hard cap (never exceeded)
REBALANCE_MIN_DELTA = 0.005
LEARN_EVERY = 5                                # sessions between learn steps (~weekly)

# learnable params + HARD bounds the learner may never cross
DEFAULT_PARAMS = {"gate": 0.33, "max_positions": 20, "exposure": 1.0}
BOUNDS = {"gate": (0.25, 0.45), "max_positions": (10, 25), "exposure": (0.5, 1.0)}


# --- io helpers ------------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def _save(path, obj):
    path.write_text(json.dumps(obj, indent=2))


def _append(path, row: dict):
    header = not path.exists()
    pd.DataFrame([row]).to_csv(path, mode="a", header=header, index=False)


def _log_change(event: dict):
    with CHANGELOG.open("a") as f:
        f.write(json.dumps(event) + "\n")


def _matrices():
    C, O = {}, {}
    for tk in all_tickers(include_benchmarks=False):
        df = load_prices(tk)
        if df is not None and "Close" in df:
            C[tk] = df["Close"]
            if "Open" in df:
                O[tk] = df["Open"]
    return (pd.DataFrame(C).sort_index().ffill(),
            pd.DataFrame(O).sort_index().ffill())


# --- model / version control ----------------------------------------------
def _load_model() -> dict:
    m = _load(MODEL, None)
    if m is None:
        m = {"version": 1, "params": dict(DEFAULT_PARAMS), "parent": None,
             "activated": _now(), "note": "baseline"}
        _save(MODEL, m)
        _save(VERSIONS / "v1.json", m)
        _log_change({"ts": _now(), "event": "create", "version": 1, "parent": None,
                     "params": m["params"], "changed": {}, "reason": "baseline",
                     "perf_before": None})
    return m


def _bump_version(model, new_params, event, reason, perf_before) -> dict:
    changed = {k: [model["params"][k], new_params[k]]
               for k in new_params if new_params[k] != model["params"][k]}
    nm = {"version": model["version"] + 1, "params": new_params,
          "parent": model["version"], "activated": _now(), "note": reason}
    _save(MODEL, nm)
    _save(VERSIONS / f"v{nm['version']}.json", nm)
    _log_change({"ts": _now(), "event": event, "version": nm["version"],
                 "parent": model["version"], "params": new_params,
                 "changed": changed, "reason": reason, "perf_before": perf_before})
    return nm


def _clip(k, v):
    lo, hi = BOUNDS[k]
    return float(min(hi, max(lo, v))) if k != "max_positions" else int(min(hi, max(lo, round(v))))


# --- the learner (transparent, bounded, reversible) ------------------------
def _version_perf(perf: pd.DataFrame, version: int) -> dict | None:
    v = perf[perf["version"] == version]
    if len(v) < 2:
        return None
    eq = v["equity"].to_numpy()
    dd = float((v["equity"] / v["equity"].cummax() - 1).min())
    return {"days": int(len(v)), "return": round(float(eq[-1] / eq[0] - 1), 4),
            "drawdown": round(dd, 4),
            "daily_mean": round(float(v["daily_pnl"].mean()), 2)}


def maybe_learn(model: dict, perf: pd.DataFrame) -> dict:
    """Evaluate the live version; adjust one knob or revert. Returns model."""
    vperf = _version_perf(perf, model["version"])
    if vperf is None or vperf["days"] < LEARN_EVERY:
        return model                                       # not enough data yet

    params = dict(model["params"])
    # 1) rollback guard — did this version do worse per-day than its parent?
    if model["parent"] is not None:
        pperf = _version_perf(perf, model["parent"])
        if pperf and vperf["daily_mean"] < pperf["daily_mean"]:
            parent = _load(VERSIONS / f"v{model['parent']}.json", None)
            if parent:
                return _bump_version(
                    model, dict(parent["params"]), "revert",
                    f"v{model['version']} daily P&L {vperf['daily_mean']} < parent "
                    f"v{model['parent']} {pperf['daily_mean']} — rolled back", vperf)

    # 2) drawdown-responsive exposure controller
    dd, r = vperf["drawdown"], vperf["return"]
    if dd <= -0.08:
        params["exposure"] = _clip("exposure", params["exposure"] - 0.15)
        reason = f"drawdown {dd:.1%} over {vperf['days']}d — cut exposure (de-risk)"
    elif dd >= -0.03 and r > 0:
        params["exposure"] = _clip("exposure", params["exposure"] + 0.10)
        reason = f"calm & positive ({r:+.1%}, dd {dd:.1%}) — restore exposure"
    else:
        # no change warranted; re-anchor the clock by re-activating same version
        model["activated"] = _now()
        _save(MODEL, model)
        return model

    if params == model["params"]:
        return model
    return _bump_version(model, params, "adjust", reason, vperf)


# --- account mechanics -----------------------------------------------------
def _load_state() -> dict:
    return _load(STATE, {"created": _now(), "capital": START_CAPITAL,
                         "cash": START_CAPITAL, "positions": {},
                         "last_cycle_date": None,
                         "totals": {"fees_paid": 0.0, "trades": 0, "realized_pnl": 0.0}})


def _value(st, prices) -> float:
    v = st["cash"]
    for tk, pos in st["positions"].items():
        px = prices.get(tk)
        if px is not None and not np.isnan(px):
            v += pos["shares"] * float(px)
    return v


def _target(C, asof, params) -> pd.Series:
    s = score_matrix(C).loc[asof].dropna()
    s = s[s >= params["gate"]].sort_values(ascending=False).head(params["max_positions"])
    w = pd.Series(0.0, index=C.columns)
    if len(s):
        w[s.index] = PER_NAME_CAP * params["exposure"]     # <=5% per name
    return w


def _rebalance_open(st, C, O, today, prior, params, day) -> tuple[int, float]:
    opens = O.loc[today]
    target_w = _target(C.loc[:prior], prior, params)        # leak-safe
    value = _value(st, opens)
    tgt = (target_w * value).reindex(C.columns).fillna(0.0)
    cur_sh = {tk: st["positions"].get(tk, {}).get("shares", 0.0) for tk in C.columns}
    cur = pd.Series({tk: cur_sh[tk] * float(opens.get(tk, np.nan)) for tk in C.columns}).fillna(0.0)
    delta = tgt - cur
    order = list(delta[delta < 0].sort_values().index) + list(delta[delta > 0].sort_values(ascending=False).index)
    trades, fees = 0, 0.0
    for tk in order:
        px = float(opens.get(tk, np.nan))
        if np.isnan(px) or px <= 0 or abs(float(delta[tk])) < max(REBALANCE_MIN_DELTA * value, 1.0):
            continue
        side = "buy" if delta[tk] > 0 else "sell"
        fp = _fill_price(side, px)
        shares = abs(float(delta[tk])) / fp
        if side == "sell":
            shares = min(shares, cur_sh[tk])
            if shares <= 0:
                continue
        fee = trade_fees(side, shares, fp)
        pos = st["positions"].get(tk, {"shares": 0.0, "avg_cost": 0.0})
        if side == "buy":
            st["cash"] -= shares * fp + fee["total_fee"]
            new = pos["shares"] + shares
            pos["avg_cost"] = (pos["shares"] * pos["avg_cost"] + shares * fp) / new
            pos["shares"] = new
        else:
            st["cash"] += shares * fp - fee["total_fee"]
            st["totals"]["realized_pnl"] = round(
                st["totals"]["realized_pnl"] + shares * (fp - pos["avg_cost"]), 2)
            pos["shares"] -= shares
        st["positions"].pop(tk, None) if pos["shares"] <= 1e-9 else st["positions"].__setitem__(tk, pos)
        fees += fee["total_fee"]
        trades += 1
        _append(TRADES, {"date": day, "side": side, "ticker": tk,
                         "shares": round(shares, 6), "ref_price": round(px, 4),
                         "fill_price": round(fp, 4), **fee,
                         "cash_after": round(st["cash"], 2)})
    st["totals"]["trades"] += trades
    st["totals"]["fees_paid"] = round(st["totals"]["fees_paid"] + fees, 2)
    return trades, round(fees, 2)


# --- the one daily call ----------------------------------------------------
def run_cycle(asof=None) -> dict:
    C, O = _matrices()
    if C.empty:
        return {"error": "no price data — run download first"}
    idx = C.index
    today = idx[-1] if asof is None else idx[idx <= pd.Timestamp(asof)][-1]
    i = idx.get_loc(today)
    if i < 260:
        return {"error": "not enough history at this date"}
    prior = idx[i - 1]
    day = str(pd.Timestamp(today).date())

    st = _load_state()
    if st["last_cycle_date"] == day:
        return {"skipped": f"cycle already run for {day}"}
    model = _load_model()

    # 1) SETTLE prior close
    prior_close = C.loc[prior]
    eq_prior = _value(st, prior_close)
    prev_eq = st["capital"]
    if PERF.exists():
        pv = pd.read_csv(PERF)
        if len(pv):
            prev_eq = float(pv["equity"].iloc[-1])
    _append(PERF, {"date": str(pd.Timestamp(prior).date()), "version": model["version"],
                   "equity": round(eq_prior, 2), "cash": round(st["cash"], 2),
                   "positions_value": round(eq_prior - st["cash"], 2),
                   "daily_pnl": round(eq_prior - prev_eq, 2),
                   "cum_return": round(eq_prior / st["capital"] - 1, 4),
                   "exposure": model["params"]["exposure"], "gate": model["params"]["gate"],
                   "max_positions": model["params"]["max_positions"]})

    # 2) LEARN (if due)
    perf = pd.read_csv(PERF)
    before_v = model["version"]
    model = maybe_learn(model, perf)
    learned = None if model["version"] == before_v else {
        "from": before_v, "to": model["version"], "note": model["note"]}

    # 3) TRADE at today's open
    trades, fees = _rebalance_open(st, C, O, today, prior, model["params"], day)
    st["last_cycle_date"] = day
    _save(STATE, st)

    value_now = _value(st, O.loc[today])
    return {"date": day, "model_version": model["version"], "learned": learned,
            "params": model["params"], "trades": trades, "fees_today": fees,
            "cash": round(st["cash"], 2), "positions": len(st["positions"]),
            "portfolio_value": round(value_now, 2),
            "prior_close_equity": round(eq_prior, 2),
            "cum_return_pct": round((eq_prior / st["capital"] - 1) * 100, 2),
            "fees_paid_todate": st["totals"]["fees_paid"]}


def status() -> dict:
    st, model = _load_state(), _load_model()
    C, _ = _matrices()
    eq = _value(st, C.loc[C.index[-1]])
    return {"model_version": model["version"], "params": model["params"],
            "equity": round(eq, 2), "cash": round(st["cash"], 2),
            "cum_return_pct": round((eq / st["capital"] - 1) * 100, 2),
            "positions": len(st["positions"]),
            "fees_paid_todate": st["totals"]["fees_paid"]}


def reset(capital: float = START_CAPITAL):
    for p in (STATE, MODEL, CHANGELOG, PERF, TRADES):
        if p.exists():
            p.unlink()
    for f in VERSIONS.glob("*.json"):
        f.unlink()
    st = _load_state()
    st["capital"] = st["cash"] = capital
    _save(STATE, st)
    _load_model()
