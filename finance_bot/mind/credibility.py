"""
Source credibility — the "be aware of dishonest news" layer.

Two independent ideas, deliberately kept separate:

1. SOURCE PRIOR (this file): a static, human-set trust weight per outlet in
   [0, 1]. A tabloid rumor and a filed 10-K should NOT enter the mind with the
   same authority. You are meant to edit these by hand — they encode judgement.

2. CORROBORATION (computed at event time, see ingest/news.py): an event's
   confidence rises when *multiple independent* sources report the same thing
   within a short window, and falls when only one low-trust source carries it.

A raw headline's influence on the mind is:

      influence = source_prior * corroboration * recency_decay

So a single sensational story from a low-trust source barely moves anything,
while the same claim confirmed by a filing and two wires moves it a lot. This
is precisely the mechanism that stops you "jumping off a building" because one
outlet screamed that a stock is going to zero.
"""

from __future__ import annotations

# Static trust priors. TUNE THESE BY HAND. Higher = more trustworthy.
# Regulatory filings and primary documents rank highest; opinion/aggregators
# and single-source rumor rank lowest.
SOURCE_PRIOR: dict[str, float] = {
    # primary / regulatory (highest trust)
    "sec_filing": 0.98,
    "company_ir": 0.95,        # company investor-relations / earnings release
    "fed_gov": 0.95,           # central banks, official statistics
    # major wires / established financial press
    "reuters": 0.90,
    "bloomberg": 0.90,
    "apnews": 0.88,
    "bbc": 0.85,
    "wsj": 0.85,
    "ft": 0.85,
    "cnbc": 0.75,
    "fox_business": 0.70,      # "fox finance" per the brief
    "marketwatch": 0.70,
    # aggregators / mixed quality
    "yahoo_finance": 0.65,
    "seekingalpha": 0.55,
    "benzinga": 0.50,
    # social / rumor (lowest — treat as leads to verify, never as fact)
    "reddit": 0.25,
    "stocktwits": 0.20,
    "x_twitter": 0.20,
    "unknown": 0.30,
}

DEFAULT_PRIOR = 0.30


def source_prior(source: str) -> float:
    """Trust weight for a source key; unknown sources get DEFAULT_PRIOR."""
    return SOURCE_PRIOR.get(source, DEFAULT_PRIOR)


def corroboration(n_independent_sources: int,
                  mean_source_prior: float) -> float:
    """
    Map (# independent sources, their avg trust) -> a multiplier in ~[0.3, 1.3].

    - 1 low-trust source  -> < 1  (discounted)
    - several trusted sources agreeing -> > 1 (amplified, capped)
    Uses a saturating curve so the 5th confirmation adds little.
    """
    import math
    base = 1.0 - math.exp(-max(n_independent_sources, 0) / 2.0)  # 0..1 saturating
    trust = 0.5 + mean_source_prior            # 0.5..1.5 shift by avg trust
    return round(max(0.3, min(1.3, (0.4 + base) * trust)), 3)


def recency_decay(age_days: float, half_life_days: float = 5.0) -> float:
    """Exponential decay so stale news fades from the mind."""
    import math
    return round(math.exp(-max(age_days, 0.0) * math.log(2) / half_life_days), 4)


def influence(source: str, n_sources: int, mean_prior: float,
              age_days: float) -> float:
    """Combined influence weight of an event on the mind (see module docstring)."""
    return round(
        source_prior(source)
        * corroboration(n_sources, mean_prior)
        * recency_decay(age_days),
        4,
    )
