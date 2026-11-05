"""
News accuracy ledger + per-outlet reliability learning.

The idea: stop treating every headline as equally trustworthy. Log what each
OUTLET called (which themes, which direction), then — a few days later — check
whether the called move actually happened. Outlets that are repeatedly right
earn a higher reliability weight; ones that cry wolf get discounted. That weight
then scales how much their calls move the book (see analyze/decide.py, which
also raises the overall news weight to 0.30).

Flow, all leak-free for TRADING (reliability at decision time only uses calls
that have already resolved):
  1. log_calls(news_tilt, asof)   -> append today's unresolved calls
  2. resolve_due(close_df, asof)  -> grade calls whose horizon has elapsed,
                                     update per-outlet hit/total
  3. reliability(source)          -> Bayesian-smoothed hit rate in [0,1]

Files (committed with the rest of FNCBOT state):
  FNCBOT/news_log.jsonl         one line per (event, theme) call
  FNCBOT/outlet_reliability.json  {source: {hits, total, reliability}}
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np

from finance_bot import config
from finance_bot.universe import THEMES

LOG_FILE = config.ROOT / "FNCBOT" / "news_log.jsonl"
REL_FILE = config.ROOT / "FNCBOT" / "outlet_reliability.json"

HORIZON = 5          # trading days to judge a call
PRIOR_A = 2.0        # Beta prior: a new/unseen outlet starts neutral at 0.5
PRIOR_B = 2.0
MIN_THEME_MOVE = 0.0  # |theme return| must exceed this to count as a real move


# ── reliability store ────────────────────────────────────────────────────────
def load_reliability() -> dict:
    if REL_FILE.exists():
        try:
            return json.loads(REL_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_reliability(rel: dict) -> None:
    REL_FILE.parent.mkdir(parents=True, exist_ok=True)
    REL_FILE.write_text(json.dumps(rel, indent=2, sort_keys=True))


def reliability(source: str, rel: dict | None = None) -> float:
    """Smoothed hit rate for an outlet, in [0,1]; 0.5 until it has a track record."""
    rel = load_reliability() if rel is None else rel
    r = rel.get(source)
    if not r:
        return PRIOR_A / (PRIOR_A + PRIOR_B)          # 0.5
    return (r["hits"] + PRIOR_A) / (r["total"] + PRIOR_A + PRIOR_B)


# ── logging ──────────────────────────────────────────────────────────────────
def _read_log() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    out = []
    for line in LOG_FILE.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def _write_log(rows: list[dict]) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text("\n".join(json.dumps(r) for r in rows) + ("\n" if rows else ""))


def log_calls(news_tilt: dict, asof: str) -> int:
    """Append today's calls: one per (event source, theme it drove) with the
    theme's signed tilt that day. Idempotent per (date, source, theme)."""
    themes = news_tilt.get("themes", {}) if isinstance(news_tilt, dict) else {}
    events = news_tilt.get("events", []) if isinstance(news_tilt, dict) else []
    rows = _read_log()
    seen = {(r["date"], r["source"], r["theme"]) for r in rows}
    added = 0
    for ev in events:
        src = (ev.get("source") or "unknown").strip().lower()
        for th in ev.get("themes", []):
            tilt = float(themes.get(th, 0.0))
            if tilt == 0.0 or (asof, src, th) in seen:
                continue
            rows.append({
                "date": asof, "source": src, "theme": th, "tilt": round(tilt, 3),
                "headline": (ev.get("headline") or "")[:160],
                "horizon": HORIZON, "resolved": False, "ret": None, "correct": None,
                "logged": datetime.now(timezone.utc).isoformat(),
            })
            seen.add((asof, src, th))
            added += 1
    _write_log(rows)
    return added


# ── resolution + learning ────────────────────────────────────────────────────
def _theme_return(close_df, theme: str, d0, d1) -> float | None:
    ticks = [t for t in THEMES.get(theme, []) if t in close_df.columns]
    if not ticks:
        return None
    sub = close_df.loc[d0:d1, ticks]
    if len(sub) < 2:
        return None
    rets = (sub.iloc[-1] / sub.iloc[0] - 1).dropna()
    return float(rets.mean()) if len(rets) else None


def resolve_due(close_df, asof: str) -> dict:
    """Grade every call whose horizon has elapsed; update outlet reliability.
    A call is correct when the theme's equal-weight return over the horizon moved
    in the called direction. Returns a small summary."""
    rows = _read_log()
    rel = load_reliability()
    idx = close_df.index
    resolved = 0
    for r in rows:
        if r["resolved"]:
            continue
        d0 = r["date"]
        locs = idx[idx >= d0]
        if len(locs) == 0:
            continue
        start = locs[0]
        i = idx.get_loc(start)
        if i + r["horizon"] >= len(idx):
            continue                                  # horizon not elapsed yet
        end = idx[i + r["horizon"]]
        ret = _theme_return(close_df, r["theme"], start, end)
        if ret is None:
            continue
        correct = (np.sign(ret) == np.sign(r["tilt"])) and abs(ret) > MIN_THEME_MOVE
        r["resolved"], r["ret"], r["correct"] = True, round(ret, 4), bool(correct)
        src = r["source"]
        s = rel.setdefault(src, {"hits": 0, "total": 0, "reliability": 0.5})
        s["total"] += 1
        s["hits"] += int(correct)
        s["reliability"] = round((s["hits"] + PRIOR_A) / (s["total"] + PRIOR_A + PRIOR_B), 3)
        resolved += 1
    _write_log(rows)
    _save_reliability(rel)
    return {"resolved_now": resolved,
            "outlets": {k: v["reliability"] for k, v in sorted(rel.items())},
            "open_calls": sum(1 for r in rows if not r["resolved"])}


def theme_reliability_factor(news_tilt: dict, rel: dict | None = None) -> dict:
    """For each theme cited today, the mean reliability of the outlets citing it
    (0.5 if none have a track record). Used to discount themes pushed only by
    unproven/unreliable outlets."""
    rel = load_reliability() if rel is None else rel
    events = news_tilt.get("events", []) if isinstance(news_tilt, dict) else {}
    by_theme: dict[str, list[float]] = {}
    for ev in events:
        src = (ev.get("source") or "unknown").strip().lower()
        for th in ev.get("themes", []):
            by_theme.setdefault(th, []).append(reliability(src, rel))
    return {th: float(np.mean(v)) for th, v in by_theme.items()}


def report() -> str:
    rel = load_reliability()
    rows = _read_log()
    open_n = sum(1 for r in rows if not r["resolved"])
    done = [r for r in rows if r["resolved"]]
    lines = [f"News accuracy ledger — {len(rows)} calls ({len(done)} resolved, {open_n} open)\n"]
    if rel:
        lines.append(f"{'outlet':28}{'reliability':>12}{'hits/total':>12}")
        for src, s in sorted(rel.items(), key=lambda x: -x[1]["reliability"]):
            ht = f"{s['hits']}/{s['total']}"
            lines.append(f"{src:28}{s['reliability']:>12.2f}{ht:>12}")
    else:
        lines.append("(no resolved calls yet — reliability builds as calls mature)")
    return "\n".join(lines)
