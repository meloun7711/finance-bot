"""
Step 3 — news & events ingestion (modular adapters).

Architecture
------------
Every source is an *adapter* that yields a stream of normalized `NewsEvent`s.
Adapters are pluggable: to add "Fox finance transcripts" or a paid wire, you
write one class with a `.fetch()` method and register it — nothing downstream
changes.

Shipped adapters (all use *public* feeds, no scraping of paywalled content):
  * YahooTickerRSS   — per-ticker headline RSS, maps 1:1 to a symbol
  * GeopoliticsRSS   — world/conflict feeds, mapped to THEMES (defense, energy)

What we deliberately do NOT do here:
  * We don't scrape paywalled transcripts or bypass any site's terms. Sources
    like Fox Business / WSJ full transcripts need an API key or licensed feed;
    add them as adapters with your credentials.
  * We don't trust any single headline. Every event carries a source and the
    credibility layer (mind/credibility.py) down-weights it accordingly.

Normalized event schema is point-in-time: each event keeps the exact publish
timestamp, so the Step 4 backtest can replay history WITHOUT lookahead.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

from finance_bot import config
from finance_bot.mind.credibility import source_prior
from finance_bot.universe import THEMES, all_tickers

EVENTS_PATH = config.NEWS_DIR / "events.jsonl"

# Minimal company-name lexicon for entity matching in free-text (geopolitics,
# macro) feeds that don't carry a ticker. Extend as needed.
NAME_HINTS: dict[str, list[str]] = {
    "LMT": ["lockheed"], "RTX": ["raytheon", "rtx"], "NOC": ["northrop"],
    "GD": ["general dynamics"], "BA": ["boeing"], "PLTR": ["palantir"],
    "NVDA": ["nvidia"], "TSM": ["tsmc", "taiwan semi"], "XOM": ["exxon"],
    "CVX": ["chevron"], "MP": ["mp materials", "rare earth"],
    "IONQ": ["ionq"], "COIN": ["coinbase"], "MSTR": ["microstrategy"],
}


@dataclass
class NewsEvent:
    id: str                       # stable hash (dedup key)
    ts: str                       # ISO8601 UTC publish time (point-in-time!)
    source: str                   # credibility key, e.g. "yahoo_finance"
    headline: str
    url: str
    tickers: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    prior: float = 0.0            # source trust prior at ingest time
    body: str = ""

    @staticmethod
    def make(source: str, headline: str, url: str, ts: str,
             tickers=None, themes=None, body="") -> "NewsEvent":
        key = hashlib.sha1(
            f"{source}|{headline}|{ts}".encode("utf-8", "ignore")
        ).hexdigest()[:16]
        return NewsEvent(
            id=key, ts=ts, source=source, headline=headline, url=url,
            tickers=sorted(set(tickers or [])), themes=sorted(set(themes or [])),
            prior=source_prior(source), body=body,
        )


# --------------------------------------------------------------------------
# Entity / theme matching
# --------------------------------------------------------------------------

_CASHTAG = re.compile(r"\$([A-Z]{1,5})\b")
_UNIVERSE = set(all_tickers())


def match_tickers(text: str) -> list[str]:
    """Find universe tickers referenced by $CASHTAG or company name."""
    found = {t for t in _CASHTAG.findall(text) if t in _UNIVERSE}
    low = text.lower()
    for tk, hints in NAME_HINTS.items():
        if any(h in low for h in hints):
            found.add(tk)
    return sorted(found)


_THEME_KEYWORDS = {
    "defense": ["war", "military", "missile", "invasion", "conflict",
                "pentagon", "nato", "troops", "ceasefire", "airstrike"],
    "energy": ["oil", "opec", "crude", "gas pipeline", "sanction", "barrel"],
    "materials": ["rare earth", "lithium", "supply chain", "export ban"],
    "quantum": ["quantum computing", "qubit"],
    "ai": ["artificial intelligence", "ai chip", "data center", "llm"],
}


def match_themes(text: str) -> list[str]:
    low = text.lower()
    return sorted(th for th, kws in _THEME_KEYWORDS.items()
                  if any(k in low for k in kws))


# --------------------------------------------------------------------------
# Adapters
# --------------------------------------------------------------------------

def _http_get(url: str, timeout: float = 15.0) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": "finance-bot/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as exc:
        print(f"  ! fetch failed {url}: {type(exc).__name__}: {exc}")
        return None


def _parse_rss(xml_bytes: bytes) -> list[dict]:
    """Return [{title, link, pubDate, description}] from an RSS/Atom feed."""
    out: list[dict] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return out
    # RSS 2.0
    for item in root.iter("item"):
        out.append({
            "title": (item.findtext("title") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
            "pubDate": (item.findtext("pubDate") or "").strip(),
            "description": (item.findtext("description") or "").strip(),
        })
    # Atom fallback
    if not out:
        ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.iter(f"{ns}entry"):
            link_el = entry.find(f"{ns}link")
            out.append({
                "title": (entry.findtext(f"{ns}title") or "").strip(),
                "link": link_el.get("href") if link_el is not None else "",
                "pubDate": (entry.findtext(f"{ns}updated") or "").strip(),
                "description": (entry.findtext(f"{ns}summary") or "").strip(),
            })
    return out


def _to_iso(pubdate: str) -> str:
    """Best-effort parse of an RSS date -> ISO8601 UTC; fallback = now."""
    for parser in (parsedate_to_datetime,):
        try:
            dt = parser(pubdate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()


class YahooTickerRSS:
    """Per-ticker public headline RSS. Maps directly to one symbol."""
    source = "yahoo_finance"
    URL = ("https://feeds.finance.yahoo.com/rss/2.0/headline"
           "?s={ticker}&region=US&lang=en-US")

    def fetch(self, tickers: list[str], pause: float = 0.3) -> list[NewsEvent]:
        events: list[NewsEvent] = []
        for tk in tickers:
            raw = _http_get(self.URL.format(ticker=tk))
            if not raw:
                continue
            for item in _parse_rss(raw):
                if not item["title"]:
                    continue
                text = f"{item['title']} {item['description']}"
                events.append(NewsEvent.make(
                    source=self.source, headline=item["title"],
                    url=item["link"], ts=_to_iso(item["pubDate"]),
                    tickers=sorted({tk, *match_tickers(text)}),
                    themes=match_themes(text), body=item["description"],
                ))
            time.sleep(pause)
        return events


class GeopoliticsRSS:
    """
    World/conflict feeds. These usually carry no ticker, so they attach to
    THEMES (defense, energy, materials) and to any names their text mentions.
    Add or swap feed URLs freely.
    """
    source = "bbc"
    FEEDS = [
        "https://feeds.bbci.co.uk/news/world/rss.xml",     # BBC World (public)
        "https://feeds.bbci.co.uk/news/business/rss.xml",  # BBC Business
    ]

    def fetch(self, pause: float = 0.3) -> list[NewsEvent]:
        events: list[NewsEvent] = []
        for url in self.FEEDS:
            raw = _http_get(url)
            if not raw:
                continue
            for item in _parse_rss(raw):
                if not item["title"]:
                    continue
                text = f"{item['title']} {item['description']}"
                themes = match_themes(text)
                tickers = match_tickers(text)
                if not themes and not tickers:
                    continue  # irrelevant to the universe — drop
                events.append(NewsEvent.make(
                    source=self.source, headline=item["title"],
                    url=item["link"], ts=_to_iso(item["pubDate"]),
                    tickers=tickers, themes=themes, body=item["description"],
                ))
            time.sleep(pause)
        return events


# --------------------------------------------------------------------------
# Orchestration + persistence
# --------------------------------------------------------------------------

def _load_existing_ids() -> set[str]:
    if not EVENTS_PATH.exists():
        return set()
    ids = set()
    for line in EVENTS_PATH.read_text().splitlines():
        try:
            ids.add(json.loads(line)["id"])
        except Exception:
            continue
    return ids


def collect(tickers: list[str] | None = None,
            include_geopolitics: bool = True) -> int:
    """
    Run all adapters, dedupe against what's already stored, append new events
    to data/news/events.jsonl. Returns the number of NEW events written.
    """
    tickers = tickers or all_tickers(include_benchmarks=False)
    seen = _load_existing_ids()
    new: list[NewsEvent] = []

    for ev in YahooTickerRSS().fetch(tickers):
        if ev.id not in seen:
            seen.add(ev.id)
            new.append(ev)

    if include_geopolitics:
        for ev in GeopoliticsRSS().fetch():
            if ev.id not in seen:
                seen.add(ev.id)
                new.append(ev)

    with EVENTS_PATH.open("a") as f:
        for ev in new:
            f.write(json.dumps(asdict(ev)) + "\n")
    print(f"Collected {len(new)} new events "
          f"(total stored: {len(seen)}) -> {EVENTS_PATH}")
    return len(new)


def load_events() -> list[dict]:
    if not EVENTS_PATH.exists():
        return []
    out = []
    for line in EVENTS_PATH.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


if __name__ == "__main__":
    # Small demo run on a handful of names.
    collect(tickers=["PLTR", "NVDA", "LMT", "XOM", "IONQ", "COIN"])
