# FNCBOT news brain — output contract

The news-brain routine (WebSearch) writes **`market/news_tilt.json`** to the repo
each run. The trading engine reads it, logs every call, grades each outlet after
5 trading days, and learns a per-(outlet × theme) reliability that scales how much
that outlet moves the book. So the brain's job is **not** to decide the net view —
it is to report, per headline, **who said what, which direction, how strongly**.
The engine decides the net using learned trust.

## Output schema (write exactly this shape)

```json
{
  "as_of": "YYYY-MM-DD",
  "events": [
    {
      "headline": "one-line summary of the actual news",
      "source": "cnbc.com",
      "url": "https://…",
      "calls": [
        {"theme": "semis", "dir": "down", "strength": "strong"},
        {"theme": "ai",    "dir": "down", "strength": "moderate"}
      ]
    }
  ]
}
```

### Field rules
- **source** — the outlet's bare domain, lowercased (`cnbc.com`, `reuters.com`,
  `xtb.com`). This is the identity whose reliability is tracked, so keep it stable
  and specific. Never invent a source; if you cannot attribute a claim, drop it.
- **theme** — one of exactly these 13 (anything else is ignored):
  `defense, ai, quantum, semis, tech, cyber, energy, materials, financials,
  healthcare, space, crypto, industrial_consumer`
- **dir** — `up`, `down`, or `flat`: the direction THIS headline implies for THAT
  theme's stocks over the next week. `flat` calls are ignored by scoring.
- **strength** — `strong`, `moderate`, or `mild`: your read of the conviction /
  materiality. A central-bank shock or a sector-wide selloff is `strong`; a single
  analyst note is `mild`. Strength weights both the trade tilt and how much a
  right/wrong call moves that outlet's reliability — so do not inflate it.
- One event may carry several `calls` (a story that hits semis *and* energy).
- Report the move the news implies, **not** whether you agree. If an outlet is
  wrong, the ledger will learn that on its own — your job is faithful attribution.

### Honesty rules (unchanged)
- Prefer primary, reputable outlets; attribute each call to the outlet that made
  it. Do not merge several outlets into one `source`.
- Beware promotional or low-quality sources — but still log them truthfully under
  their own domain; their reliability will converge to what they deserve.
- No position in `market/news_tilt.json` is advice; it is one input, capped at a
  0.30 weight and further scaled by learned reliability.

## What the engine does with it (for context)
1. `cli news-score` logs each call to `FNCBOT/news_log.jsonl` and grades matured
   ones against the theme's 5-day equal-weight return → updates
   `FNCBOT/outlet_reliability.json` (per outlet × theme, hierarchically smoothed).
2. `analyze/decide.py` computes each theme's **net tilt** = Σ(dir × strength ×
   reliability) ÷ Σ(strength × reliability), applied at `NEWS_WEIGHT = 0.30`.
3. A brand-new outlet starts at 0.50 (neutral) and earns or loses trust per theme.

The previous flat format (`{"themes": {...}, "events": [{"themes", "source"}]}`)
is still accepted as a fallback, but emit `calls` so each outlet is graded on its
own claim, not the theme consensus.
