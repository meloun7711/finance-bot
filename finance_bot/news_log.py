"""
News accuracy ledger + per-(outlet x theme) reliability learning.

Each headline the news brain emits makes one or more CALLS: for a theme, a
direction (up/down) and a strength (strong/moderate/mild). We log every call,
and a few days later grade whether that theme's stocks actually moved the way
the OUTLET called it. Outlets that are repeatedly right on a theme earn trust on
THAT theme; ones that cry wolf get discounted. That learned trust then scales
how much their calls move the book (analyze/decide.py, news weight 0.30).

Why per-(outlet x theme): an outlet can be sharp on semis and useless on energy.
Sparse cells are smoothed hierarchically — a thin (outlet, theme) cell backs off
to that outlet's overall hit rate, which backs off to a neutral 0.5 prior — so a
new outlet/theme starts neutral and only departs from it with evidence.

Strength matters twice: a strong call tilts the trade more AND moves reliability
more when it resolves (right or wrong).

Leak-free for trading: reliability at decision time uses only resolved calls.

Files (committed with FNCBOT state):
  FNCBOT/news_log.jsonl           one line per (date, outlet, theme) call
  FNCBOT/outlet_reliability.json  {source: {theme: {a,b,reliability}, ...}}

News-brain output contract (market/news_tilt.json) — see deploy/news_brain.md:
  {"as_of","events":[{"headline","source","calls":[
       {"theme","dir":"up|down|flat","strength":"strong|moderate|mild"}]}]}
Old format ({"themes":{...},"events":[{themes,source}]}) is still accepted.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np

from finance_bot import config
from finance_bot.universe import THEMES

LOG_FILE = config.ROOT / "FNCBOT" / "news_log.jsonl"
REL_FILE = config.ROOT / "FNCBOT" / "outlet_reliability.json"

HORIZON = 5                     # trading days to judge a call
PRIOR = 2.0                     # shrinkage strength at each hierarchy level
DIR = {"up": 1, "down": -1, "flat": 0, "neutral": 0, "": 0}
STRENGTH = {"strong": 1.0, "moderate": 0.6, "mild": 0.3, "weak": 0.3}


def _dir(x) -> int:
    if isinstance(x, (int, float)):
        return int(np.sign(x))
    return DIR.get(str(x).strip().lower(), 0)


def _strength(x) -> float:
    if isinstance(x, (int, float)):
        return float(min(max(abs(x), 0.0), 1.0))
    return STRENGTH.get(str(x).strip().lower(), 0.6)


def _iter_calls(news: dict):
    """Yield (source, theme, sign, strength) from either schema.

    New: events[].calls[] with dir+strength. Old: a themes{} net sign attributed
    to each event that lists the theme, at moderate strength.
    """
    if not isinstance(news, dict):
        return
    events = news.get("events", []) or []
    legacy_themes = news.get("themes", {}) or {}
    for ev in events:
        src = (ev.get("source") or "unknown").strip().lower()
        calls = ev.get("calls")
        if calls:                                   # new schema
            for c in calls:
                th = c.get("theme")
                if th in THEMES:
                    s = _dir(c.get("dir"))
                    if s != 0:
                        yield src, th, s, _strength(c.get("strength"))
        else:                                       # old schema fallback
            for th in ev.get("themes", []):
                if th in THEMES:
                    s = _dir(legacy_themes.get(th, 0.0))
                    if s != 0:
                        yield src, th, s, 0.6


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


def _beta_rate(a: float, b: float, prior_rate: float) -> float:
    """Posterior mean of a Beta with `PRIOR` pseudo-obs pulled toward prior_rate."""
    return (a + PRIOR * prior_rate) / (a + b + PRIOR)


def reliability(source: str, theme: str | None = None, rel: dict | None = None) -> float:
    """Trust in [0,1]. Hierarchical: (outlet x theme) -> outlet overall -> 0.5.

    A thin (outlet, theme) cell is shrunk toward the outlet's overall rate, which
    is itself shrunk toward the neutral 0.5 prior. Unknown outlet -> 0.5.
    """
    rel = load_reliability() if rel is None else rel
    src = rel.get(source)
    if not src:
        return 0.5
    # outlet overall, pooled across its themes, shrunk toward 0.5
    A = sum(c["a"] for c in src.values()); B = sum(c["b"] for c in src.values())
    overall = _beta_rate(A, B, 0.5)
    if theme is None:
        return round(overall, 3)
    cell = src.get(theme)
    if not cell:
        return round(overall, 3)                    # no theme history -> outlet overall
    return round(_beta_rate(cell["a"], cell["b"], overall), 3)


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


def log_calls(news: dict, asof: str) -> int:
    """Append today's calls, one per (date, outlet, theme). Idempotent; if an
    outlet repeats a theme the same day, keep the strongest-conviction call."""
    rows = _read_log()
    idx = {(r["date"], r["source"], r["theme"]): i for i, r in enumerate(rows)}
    added = 0
    for src, th, sign, stg in _iter_calls(news):
        key = (asof, src, th)
        rec = {"date": asof, "source": src, "theme": th, "sign": sign,
               "strength": round(stg, 2), "horizon": HORIZON,
               "resolved": False, "ret": None, "correct": None,
               "logged": datetime.now(timezone.utc).isoformat()}
        if key in idx:
            cur = rows[idx[key]]
            if not cur["resolved"] and stg > cur["strength"]:
                rows[idx[key]] = rec                # upgrade to the stronger call
        else:
            rows.append(rec); idx[key] = len(rows) - 1; added += 1
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
    """Grade calls whose horizon has elapsed; update per-(outlet, theme) trust.
    Correct = theme moved in the called direction. Strength weights the update."""
    rows = _read_log()
    rel = load_reliability()
    idx = close_df.index
    resolved = 0
    for r in rows:
        if r["resolved"]:
            continue
        locs = idx[idx >= r["date"]]
        if len(locs) == 0:
            continue
        i = idx.get_loc(locs[0])
        if i + r["horizon"] >= len(idx):
            continue                                # horizon not elapsed yet
        ret = _theme_return(close_df, r["theme"], locs[0], idx[i + r["horizon"]])
        if ret is None:
            continue
        correct = (np.sign(ret) == r["sign"])
        r["resolved"], r["ret"], r["correct"] = True, round(ret, 4), bool(correct)
        w = float(r["strength"])                    # strong calls move trust more
        cell = rel.setdefault(r["source"], {}).setdefault(
            r["theme"], {"a": 0.0, "b": 0.0, "reliability": 0.5})
        cell["a" if correct else "b"] += w
        cell["reliability"] = reliability(r["source"], r["theme"], rel)
        resolved += 1
    _write_log(rows)
    _save_reliability(rel)
    open_calls = sum(1 for r in rows if not r["resolved"])
    return {"resolved_now": resolved, "open_calls": open_calls}


def net_theme_tilts(news: dict, rel: dict | None = None) -> dict:
    """Reliability- and strength-weighted consensus direction per theme, in
    [-1,1]. This REPLACES any brain-emitted net tilt: the brain reports who said
    what, the engine decides the net using learned trust."""
    rel = load_reliability() if rel is None else rel
    acc: dict[str, list[float]] = {}                # theme -> [num, den]
    for src, th, sign, stg in _iter_calls(news):
        w = stg * reliability(src, th, rel)
        a = acc.setdefault(th, [0.0, 0.0])
        a[0] += sign * w
        a[1] += w
    return {th: (num / den if den else 0.0) for th, (num, den) in acc.items()}


def report() -> str:
    rel = load_reliability()
    rows = _read_log()
    done = [r for r in rows if r["resolved"]]
    open_n = len(rows) - len(done)
    out = [f"News accuracy ledger — {len(rows)} calls ({len(done)} resolved, {open_n} open)\n"]
    if not rel:
        out.append("(no resolved calls yet — reliability builds as calls mature)")
        return "\n".join(out)
    out.append(f"{'outlet':24}{'theme':16}{'reliability':>12}{'a/b (w)':>12}")
    for src in sorted(rel):
        out.append(f"{src}  (overall {reliability(src):.2f})")
        for th, c in sorted(rel[src].items(), key=lambda x: -x[1]["reliability"]):
            ab = f"{c['a']:.1f}/{c['b']:.1f}"
            out.append(f"{'':24}{th:16}{c['reliability']:>12.2f}{ab:>12}")
    return "\n".join(out)
