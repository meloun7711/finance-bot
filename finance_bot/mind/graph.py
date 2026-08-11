"""
Step 2 — the "modular mind": a graph over the universe.

Each stock is a node. Edges encode *relationships the mind will reason over*:

  * theme       — a soft prior: two names share a sector/theme bucket
  * corr        — realized return correlation over the sample
  * leadlag     — one name's returns lead another's by k days (directional)

NOTE ON LEAD/LAG: at DAILY frequency, equity cross-correlations at a lag are
empirically tiny (median |ρ|≈0.03, rarely >0.16 even among strongly co-moving
names) — markets are efficient enough that yesterday's move in A barely
predicts today's move in B. So leadlag edges are FEW and LOW-CONFIDENCE by
construction: treat them as weak hints, never as standalone signals. The real
directional signal comes from the news event-study (Step 4): an event on a
"leader" name and the forward return it precedes in a "follower".

Why three edge types?
  A pure correlation graph can't tell you *direction* (does NVDA lead SMCI, or
  the reverse?). The lead/lag edge is what later lets a news shock on one node
  propagate to the names it tends to drag along, with the right time offset.

The graph is stored as plain JSON (data/graph/mind.json) — no heavyweight
graph library — so it stays inspectable and diffable.

IMPORTANT: correlation here is descriptive, not predictive. It is measured on
history and will drift. Step 4's backtest is what tells you whether an edge is
actually tradable.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from finance_bot import config
from finance_bot.ingest.prices import load_close_matrix
from finance_bot.universe import all_tickers, themes_map

GRAPH_PATH = config.GRAPH_DIR / "mind.json"


@dataclass
class Edge:
    src: str
    dst: str
    kind: str           # "theme" | "corr" | "leadlag"
    weight: float       # correlation coeff, or lead/lag corr at best lag
    lag: int = 0        # days src leads dst (leadlag only); >0 => src leads


def _returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily log returns, columns aligned to tickers."""
    return np.log(prices / prices.shift(1)).dropna(how="all")


def _corr_edges(rets: pd.DataFrame, threshold: float,
                min_overlap: int) -> list[Edge]:
    """Undirected correlation edges above |threshold|."""
    corr = rets.corr(min_periods=min_overlap)
    edges: list[Edge] = []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            c = corr.at[a, b]
            if pd.notna(c) and abs(c) >= threshold:
                edges.append(Edge(a, b, "corr", round(float(c), 4)))
    return edges


def _leadlag_edges(rets: pd.DataFrame, threshold: float, max_lag: int,
                   min_overlap: int) -> list[Edge]:
    """
    Directional edges: for each pair, find the lag k in [1, max_lag] that
    maximizes corr(a_t-k, b_t). If that beats the same-day corr and the
    threshold, record a directed edge a -> b (a leads b by k days).
    Only computed for pairs that are already contemporaneously related, to
    keep it O(reasonable).
    """
    edges: list[Edge] = []
    cols = list(rets.columns)
    same_day = rets.corr(min_periods=min_overlap)
    for i, a in enumerate(cols):
        for b in cols:
            if a == b:
                continue
            base = same_day.at[a, b]
            if pd.isna(base) or abs(base) < threshold * 0.8:
                continue  # unrelated even contemporaneously — skip
            best_lag, best_c = 0, base
            for k in range(1, max_lag + 1):
                c = rets[a].shift(k).corr(rets[b], min_periods=min_overlap)
                if pd.notna(c) and abs(c) > abs(best_c):
                    best_lag, best_c = k, c
            if best_lag > 0 and abs(best_c) >= threshold:
                edges.append(Edge(a, b, "leadlag",
                                  round(float(best_c), 4), lag=best_lag))
    return edges


def build_graph(tickers: list[str] | None = None,
                corr_threshold: float = 0.5,
                leadlag_threshold: float = 0.10,
                max_lag: int = 3,
                min_overlap: int = 250) -> dict:
    """
    Build and persist the mind graph.

    Returns the graph dict (also written to GRAPH_PATH).
    """
    tickers = tickers or all_tickers()
    prices = load_close_matrix(tickers)
    if prices.empty:
        raise RuntimeError("No price data on disk — run Step 1 (download) first.")

    prices = prices.dropna(axis=1, how="all")
    rets = _returns(prices)
    tmap = themes_map()

    edges: list[Edge] = []

    # 1) theme priors (undirected, weight = 1.0 marker)
    theme_groups: dict[str, list[str]] = {}
    for tk in prices.columns:
        for th in tmap.get(tk, []):
            theme_groups.setdefault(th, []).append(tk)
    for th, members in theme_groups.items():
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                edges.append(Edge(a, b, "theme", 1.0))

    # 2) realized correlation
    edges += _corr_edges(rets, corr_threshold, min_overlap)

    # 3) lead/lag (directional)
    edges += _leadlag_edges(rets, leadlag_threshold, max_lag, min_overlap)

    graph = {
        "meta": {
            "n_nodes": int(prices.shape[1]),
            "n_edges": len(edges),
            "date_start": str(prices.index.min().date()),
            "date_end": str(prices.index.max().date()),
            "params": {
                "corr_threshold": corr_threshold,
                "leadlag_threshold": leadlag_threshold,
                "max_lag": max_lag,
                "min_overlap": min_overlap,
            },
        },
        "nodes": {tk: {"themes": tmap.get(tk, [])} for tk in prices.columns},
        "edges": [asdict(e) for e in edges],
    }
    GRAPH_PATH.write_text(json.dumps(graph, indent=2))
    return graph


# --------------------------------------------------------------------------
# Query helpers — how the rest of the system reads the mind.
# --------------------------------------------------------------------------

def load_graph() -> dict:
    if not GRAPH_PATH.exists():
        raise RuntimeError("No graph yet — run build_graph() (Step 2).")
    return json.loads(GRAPH_PATH.read_text())


def neighbors(ticker: str, kind: str | None = None,
              graph: dict | None = None) -> list[dict]:
    """
    All edges touching `ticker`. For 'leadlag', direction is preserved:
    returned dict includes 'direction' = 'leads' | 'lags'.
    """
    g = graph or load_graph()
    out: list[dict] = []
    for e in g["edges"]:
        if kind and e["kind"] != kind:
            continue
        if e["src"] == ticker:
            d = dict(e)
            d["other"] = e["dst"]
            d["direction"] = "leads" if e["kind"] == "leadlag" else "peer"
            out.append(d)
        elif e["dst"] == ticker:
            d = dict(e)
            d["other"] = e["src"]
            d["direction"] = "lags" if e["kind"] == "leadlag" else "peer"
            out.append(d)
    return sorted(out, key=lambda x: -abs(x["weight"]))


def leaders_of(ticker: str, graph: dict | None = None) -> list[dict]:
    """Names whose returns tend to LEAD `ticker` — i.e. early-warning nodes."""
    return [n for n in neighbors(ticker, kind="leadlag", graph=graph)
            if n["direction"] == "lags"]  # ticker lags them => they lead it


if __name__ == "__main__":
    g = build_graph()
    m = g["meta"]
    print(f"Mind graph: {m['n_nodes']} nodes, {m['n_edges']} edges "
          f"({m['date_start']} -> {m['date_end']})")
    kinds: dict[str, int] = {}
    for e in g["edges"]:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    for k, v in kinds.items():
        print(f"  {k:10} {v}")
