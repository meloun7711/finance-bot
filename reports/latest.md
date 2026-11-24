# FNCBOT Decisions — 2026-11-23

_Model output, not advice. Data through 2026-11-23; 243 names. Paper/research signals for review — not auto-executed._

## News tilt (reliability-weighted consensus, news weight 0.30)
Net direction per theme = each outlet's call (up/down × strength) weighted by how reliable that outlet has been on that theme.

| Theme | Net tilt | Applied (×0.30) |
|-------|---------:|----------------:|
| ai | +0.21 | +0.064 |
| tech | +0.16 | +0.048 |
| semis | +0.14 | +0.042 |
| materials | +0.00 | +0.000 |

**Headlines (outlet → calls):**
- Nvidia board reinstates Jensen Huang as CEO after Trump pressure; shares jump 31% — _ai, semis, tech_ (cnbc.com)
- NVIDIA Board Reinstates Jensen Huang as President, CEO and Board Director — _ai, semis_ (nvidianews.nvidia.com)
- China extends suspension of expanded rare earth and lithium-battery export controls to January 10, 2027 — _materials, semis, tech_ (spglobal.com)

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
- investinglive.com (overall 0.39): energy 0.30
- khaleejtimes.com (overall 0.50): energy 0.50
- lloydslist.com (overall 0.31): defense 0.30, energy 0.24
- mining.com (overall 0.31): materials 0.20
- news.metal.com (smm) (overall 0.31): materials 0.20
- newsonair.gov.in (overall 0.69): semis 0.76, ai 0.70
- pandaforecast.com / grafa.com / sabq.org (overall 0.36): defense 0.41, energy 0.16
- spglobal.com (overall 0.50): materials 0.50
- stocktitan.net (overall 0.50): financials 0.50
- thenationalnews.com (overall 0.39): materials 0.30
- zacks.com / foxcarolina.com (overall 0.50): tech 0.50, semis 0.46, ai 0.41

## Top 15 — likely UP (news-adjusted)
| # | Ticker | Decision | Structural | News | Themes |
|---|--------|---------:|-----------:|-----:|--------|
| 1 | **PANW** | +0.67 | +0.63 | +0.16 | tech,cyber |
| 2 | **AMD** | +0.65 | +0.58 | +0.21 | ai,semis |
| 3 | **DELL** | +0.64 | +0.57 | +0.21 | ai |
| 4 | **OKTA** | +0.62 | +0.62 | +0.00 | cyber |
| 5 | **VRNS** | +0.61 | +0.61 | +0.00 | cyber |
| 6 | **MPC** | +0.61 | +0.61 | +0.00 | energy |
| 7 | **TGT** | +0.61 | +0.61 | +0.00 | industrial_consumer |
| 8 | **CRWD** | +0.60 | +0.60 | +0.00 | cyber |
| 9 | **TWLO** | +0.60 | +0.53 | +0.21 | ai |
| 10 | **PSX** | +0.60 | +0.60 | +0.00 | energy |
| 11 | **TENB** | +0.59 | +0.59 | +0.00 | cyber |
| 12 | **VLO** | +0.59 | +0.59 | +0.00 | energy |
| 13 | **MU** | +0.59 | +0.55 | +0.14 | semis |
| 14 | **SAIC** | +0.59 | +0.59 | +0.00 | defense |
| 15 | **MRVL** | +0.59 | +0.54 | +0.14 | semis |

## Bottom 8 — likely DOWN
- JOBY -0.80 (space)
- LAES -0.79 (quantum)
- RGTI -0.77 (quantum)
- QBTS -0.75 (quantum)
- KTOS -0.75 (defense)
- ACHR -0.74 (space)
- BSX -0.74 (healthcare)
- BBAI -0.73 (ai)

## Dip-in-uptrend (strong long-term, pulling back now)
- **ESTC** — 20d -25.9%, -26.0% off recent high
- **MPC** — 20d -22.3%, -24.6% off recent high
- **VLO** — 20d -21.9%, -27.6% off recent high
- **GTLB** — 20d -21.3%, -23.1% off recent high
- **SNOW** — 20d -18.9%, -26.4% off recent high
- **CRWD** — 20d -17.9%, -22.9% off recent high
- **PSX** — 20d -16.4%, -18.8% off recent high
- **AMD** — 20d -13.6%, -29.4% off recent high
- **NET** — 20d -11.3%, -18.3% off recent high
- **COP** — 20d -10.2%, -11.7% off recent high
- **CVX** — 20d -9.8%, -11.2% off recent high
- **EOG** — 20d -9.4%, -10.5% off recent high
