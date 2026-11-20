# FNCBOT Decisions — 2026-11-19

_Model output, not advice. Data through 2026-11-19; 243 names. Paper/research signals for review — not auto-executed._

## News tilt (reliability-weighted consensus, news weight 0.30)
Net direction per theme = each outlet's call (up/down × strength) weighted by how reliable that outlet has been on that theme.

| Theme | Net tilt | Applied (×0.30) |
|-------|---------:|----------------:|
| ai | +0.00 | +0.000 |
| semis | +0.00 | +0.000 |
| tech | +0.00 | +0.000 |
| defense | +0.00 | +0.000 |
| energy | +0.00 | +0.000 |
| materials | +0.00 | +0.000 |
| financials | +0.00 | +0.000 |

**Headlines (outlet → calls):**
- Nvidia CEO Jensen Huang resigns abruptly amid affair/espionage-linked scandal; CFO Colette Kress named interim CEO — _ai, semis, tech_ (reuters.com (via NBC News, Washington Post, Nvidia 8-K))
- Wall Street AI-stock selloff deepens; S&P 500 hits lowest close since July as Nvidia and peers swing lower — _ai, semis, tech_ (apnews.com (via wfsb.com, stocktitan.net))
- Iran steps up tanker attacks in Strait of Hormuz as US forces conduct 'defensive strikes' on Qeshm Island; oil prices sliding on supply glut despite conflict — _defense, energy_ (oilprice.com / japantimes.co.jp / cbsnews.com)
- China extends suspension of rare earth/battery-material export controls to January 10, 2027, easing supply-chain disruption risk — _materials_ (reuters.com (via thenationalnews.com, techtimes.com))
- Fed held rates steady at Oct 28 meeting despite 'elevated' inflation; markets now price only ~10% odds of a December cut — _financials_ (apnews.com (via ajc.com, wamc.org))

**Outlet reliability (learned, per theme):**
- ajc.com (overall 0.31): financials 0.20
- aljazeera.com (overall 0.31): defense 0.30, energy 0.24
- cbsnews.com (overall 0.69): defense 0.76, energy 0.70
- cnbc.com (overall 0.77): semis 0.84, ai 0.82, financials 0.76
- datacenterknowledge.com (overall 0.31): ai 0.30, semis 0.24
- finance.yahoo.com (overall 0.31): ai 0.30, semis 0.24
- finance.yahoo.com (reuters) (overall 0.74): tech 0.80, ai 0.76, semis 0.70
- fool.com (overall 0.61): materials 0.70
- home.saxo (overall 0.15): tech 0.12, ai 0.11, semis 0.10, energy 0.09
- khaleejtimes.com (overall 0.50): energy 0.50
- mining.com (overall 0.31): materials 0.20
- news.metal.com (smm) (overall 0.31): materials 0.20
- pandaforecast.com / grafa.com / sabq.org (overall 0.36): defense 0.41, energy 0.16
- stocktitan.net (overall 0.50): financials 0.50
- thenationalnews.com (overall 0.39): materials 0.30
- zacks.com / foxcarolina.com (overall 0.50): tech 0.50, semis 0.46, ai 0.41

## Top 15 — likely UP (news-adjusted)
| # | Ticker | Decision | Structural | News | Themes |
|---|--------|---------:|-----------:|-----:|--------|
| 1 | **OKTA** | +0.63 | +0.63 | +0.00 | cyber |
| 2 | **CRWD** | +0.63 | +0.63 | +0.00 | cyber |
| 3 | **MPC** | +0.62 | +0.62 | +0.00 | energy |
| 4 | **TGT** | +0.61 | +0.61 | +0.00 | industrial_consumer |
| 5 | **PSX** | +0.61 | +0.61 | +0.00 | energy |
| 6 | **PANW** | +0.61 | +0.61 | +0.00 | tech,cyber |
| 7 | **AMD** | +0.61 | +0.61 | +0.00 | ai,semis |
| 8 | **VLO** | +0.61 | +0.61 | +0.00 | energy |
| 9 | **VRNS** | +0.59 | +0.59 | +0.00 | cyber |
| 10 | **TENB** | +0.58 | +0.58 | +0.00 | cyber |
| 11 | **FTNT** | +0.58 | +0.58 | +0.00 | cyber |
| 12 | **DELL** | +0.57 | +0.57 | +0.00 | ai |
| 13 | **TWLO** | +0.57 | +0.57 | +0.00 | ai |
| 14 | **MRNA** | +0.57 | +0.57 | +0.00 | healthcare |
| 15 | **MU** | +0.56 | +0.56 | +0.00 | semis |

## Bottom 8 — likely DOWN
- JOBY -0.80 (space)
- BBAI -0.79 (ai)
- LAES -0.79 (quantum)
- SOUN -0.79 (ai)
- AVAV -0.79 (defense)
- RGTI -0.77 (quantum)
- QBTS -0.76 (quantum)
- INDI -0.76 (semis)

## Dip-in-uptrend (strong long-term, pulling back now)
- **FTNT** — 20d -20.6%, -29.5% off recent high
- **VLO** — 20d -19.2%, -25.1% off recent high
- **MPC** — 20d -17.8%, -22.1% off recent high
- **GTLB** — 20d -15.6%, -20.6% off recent high
- **PSX** — 20d -13.0%, -16.8% off recent high
- **XOM** — 20d -8.9%, -13.3% off recent high
- **CVX** — 20d -7.5%, -11.1% off recent high
- **MRK** — 20d -6.5%, -9.1% off recent high
- **COP** — 20d -6.0%, -11.1% off recent high
- **SNOW** — 20d -5.9%, -20.0% off recent high
- **NUE** — 20d -2.3%, -9.2% off recent high
