# FNCBOT Decisions — 2026-11-20

_Model output, not advice. Data through 2026-11-20; 243 names. Paper/research signals for review — not auto-executed._

## News tilt (reliability-weighted consensus, news weight 0.30)
Net direction per theme = each outlet's call (up/down × strength) weighted by how reliable that outlet has been on that theme.

| Theme | Net tilt | Applied (×0.30) |
|-------|---------:|----------------:|
| ai | +0.00 | +0.000 |
| semis | +0.00 | +0.000 |
| tech | +0.00 | +0.000 |
| energy | +0.00 | +0.000 |
| defense | +0.00 | +0.000 |
| materials | +0.00 | +0.000 |
| financials | +0.00 | +0.000 |

**Headlines (outlet → calls):**
- Nvidia CEO Jensen Huang resigns amid board scandal; CFO Colette Kress named interim CEO, shares fall sharply — _ai, semis, tech_ (aljazeera.com)
- US tightens AI-chip export rule blocking remote access via Southeast Asian data centers as Nvidia halts China H200 shipments; AI-stock selloff deepens, S&P 500 near lowest close since July — _ai, semis, tech_ (aljazeera.com)
- Oil prices fall as Strait of Hormuz flows recover; IEA now forecasts a Q4 2026 supply surplus of ~1.7m bpd despite continued (unverified) Iranian tanker/mine incidents — _energy, defense_ (oilprice.com)
- China extends suspension of rare-earth and battery-material export controls to January 10, 2027, easing US/EU supply-chain risk — _materials_ (spglobal.com)
- FOMC minutes show officials leaning toward a December rate hike amid elevated inflation; markets price ~90% odds of a hike at the Dec 8-9 meeting — _financials_ (foxbusiness.com)

**Outlet reliability (learned, per theme):**
- ajc.com (overall 0.31): financials 0.20
- aljazeera.com (overall 0.31): defense 0.30, energy 0.24
- apnews.com (overall 0.39): financials 0.30
- cbsnews.com (overall 0.69): defense 0.76, energy 0.70
- cfr.org (overall 0.39): defense 0.30
- cnbc.com (overall 0.77): semis 0.84, ai 0.82, financials 0.76
- datacenterknowledge.com (overall 0.31): ai 0.30, semis 0.24
- digitimes.com (overall 0.61): semis 0.70
- finance.yahoo.com (overall 0.31): ai 0.30, semis 0.24
- finance.yahoo.com (reuters) (overall 0.74): tech 0.80, ai 0.76, semis 0.70
- fool.com (overall 0.61): materials 0.70
- globalcompetitionreview.com (overall 0.61): tech 0.70
- home.saxo (overall 0.15): tech 0.12, ai 0.11, semis 0.10, energy 0.09
- khaleejtimes.com (overall 0.50): energy 0.50
- mining.com (overall 0.31): materials 0.20
- news.metal.com (smm) (overall 0.31): materials 0.20
- pandaforecast.com / grafa.com / sabq.org (overall 0.36): defense 0.41, energy 0.16
- spglobal.com (overall 0.39): materials 0.30
- stocktitan.net (overall 0.50): financials 0.50
- thenationalnews.com (overall 0.39): materials 0.30
- zacks.com / foxcarolina.com (overall 0.50): tech 0.50, semis 0.46, ai 0.41

## Top 15 — likely UP (news-adjusted)
| # | Ticker | Decision | Structural | News | Themes |
|---|--------|---------:|-----------:|-----:|--------|
| 1 | **TGT** | +0.64 | +0.64 | +0.00 | industrial_consumer |
| 2 | **OKTA** | +0.63 | +0.63 | +0.00 | cyber |
| 3 | **MPC** | +0.62 | +0.62 | +0.00 | energy |
| 4 | **PANW** | +0.61 | +0.61 | +0.00 | tech,cyber |
| 5 | **CRWD** | +0.61 | +0.61 | +0.00 | cyber |
| 6 | **VRNS** | +0.61 | +0.61 | +0.00 | cyber |
| 7 | **PSX** | +0.60 | +0.60 | +0.00 | energy |
| 8 | **VLO** | +0.60 | +0.60 | +0.00 | energy |
| 9 | **AMD** | +0.58 | +0.58 | +0.00 | ai,semis |
| 10 | **TENB** | +0.58 | +0.58 | +0.00 | cyber |
| 11 | **FTNT** | +0.57 | +0.57 | +0.00 | cyber |
| 12 | **MRNA** | +0.57 | +0.57 | +0.00 | healthcare |
| 13 | **DELL** | +0.57 | +0.57 | +0.00 | ai |
| 14 | **QMCO** | +0.55 | +0.55 | +0.00 | quantum |
| 15 | **TRGP** | +0.55 | +0.55 | +0.00 | energy |

## Bottom 8 — likely DOWN
- JOBY -0.80 (space)
- BBAI -0.80 (ai)
- LAES -0.80 (quantum)
- SOUN -0.79 (ai)
- AVAV -0.79 (defense)
- RGTI -0.77 (quantum)
- QBTS -0.77 (quantum)
- INDI -0.77 (semis)

## Dip-in-uptrend (strong long-term, pulling back now)
- **GTLB** — 20d -22.0%, -24.3% off recent high
- **VLO** — 20d -19.8%, -26.8% off recent high
- **MPC** — 20d -19.6%, -24.2% off recent high
- **SNOW** — 20d -18.0%, -27.7% off recent high
- **PSX** — 20d -14.1%, -18.2% off recent high
- **XOM** — 20d -12.4%, -14.3% off recent high
- **AMD** — 20d -11.3%, -29.4% off recent high
- **CVX** — 20d -10.4%, -11.4% off recent high
- **NET** — 20d -9.9%, -18.7% off recent high
- **COP** — 20d -9.4%, -11.3% off recent high
- **MRK** — 20d -7.6%, -11.3% off recent high
- **CRWD** — 20d -7.4%, -14.5% off recent high
