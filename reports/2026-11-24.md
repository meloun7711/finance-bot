# FNCBOT Decisions — 2026-11-24

_Model output, not advice. Data through 2026-11-24; 243 names. Paper/research signals for review — not auto-executed._

## News tilt (reliability-weighted consensus, news weight 0.30)
Net direction per theme = each outlet's call (up/down × strength) weighted by how reliable that outlet has been on that theme.

| Theme | Net tilt | Applied (×0.30) |
|-------|---------:|----------------:|
| energy | -0.38 | -0.115 |
| tech | -0.22 | -0.067 |
| ai | -0.19 | -0.057 |
| semis | -0.19 | -0.057 |

**Headlines (outlet → calls):**
- AI selloff spreads from Wall Street to Asia; Nvidia, Samsung, SK Hynix, TSMC, Kioxia, SoftBank, Tokyo Electron tumble amid AI profitability/ROI doubts — _ai, semis, tech_ (cnbc.com)
- Asian stocks slide as AI selloff deepens; Kospi, Kioxia, Advantest among steepest decliners — _ai, semis, tech_ (finance.yahoo.com)
- Oil prices fall toward three-month lows as supply glut concerns offset Middle East/Strait of Hormuz disruption fears — _energy_ (cnbc.com)
- Nvidia board reinstates Jensen Huang as President/CEO/director after US government input and Trump pressure (Nov 23); shares' initial ~30% pop has since partly unwound in the broader AI-sector selloff — _ai, semis_ (nvidianews.nvidia.com)

**Outlet reliability (learned, per theme):**
- ajc.com (overall 0.31): financials 0.20
- aljazeera.com (overall 0.31): defense 0.30, energy 0.24
- apnews.com (overall 0.39): financials 0.30
- cbsnews.com (overall 0.50): defense 0.55, energy 0.50
- cfr.org (overall 0.39): defense 0.30
- cnbc.com (overall 0.78): semis 0.84, ai 0.82, financials 0.79
- datacenterknowledge.com (overall 0.31): ai 0.30, semis 0.24
- digitimes.com (overall 0.61): semis 0.70
- finance.yahoo.com (overall 0.58): semis 0.60, ai 0.54
- finance.yahoo.com (reuters) (overall 0.74): tech 0.80, ai 0.76, semis 0.70
- fool.com (overall 0.66): materials 0.76
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
| 1 | **PANW** | +0.63 | +0.63 | +0.00 | tech,cyber |
| 2 | **OKTA** | +0.62 | +0.62 | +0.00 | cyber |
| 3 | **TGT** | +0.62 | +0.62 | +0.00 | industrial_consumer |
| 4 | **VRNS** | +0.61 | +0.61 | +0.00 | cyber |
| 5 | **TENB** | +0.61 | +0.61 | +0.00 | cyber |
| 6 | **CRWD** | +0.60 | +0.60 | +0.00 | cyber |
| 7 | **S** | +0.59 | +0.59 | +0.00 | cyber |
| 8 | **SAIC** | +0.59 | +0.59 | +0.00 | defense |
| 9 | **MRNA** | +0.57 | +0.57 | +0.00 | healthcare |
| 10 | **NET** | +0.55 | +0.55 | +0.00 | cyber |
| 11 | **FTNT** | +0.55 | +0.55 | +0.00 | cyber |
| 12 | **QLYS** | +0.55 | +0.55 | +0.00 | cyber |
| 13 | **QMCO** | +0.55 | +0.55 | +0.00 | quantum |
| 14 | **AMD** | +0.51 | +0.57 | -0.19 | ai,semis |
| 15 | **DELL** | +0.51 | +0.57 | -0.19 | ai |

## Bottom 8 — likely DOWN
- SOUN -0.85 (ai)
- BBAI -0.85 (ai)
- INDI -0.83 (semis)
- JOBY -0.80 (space)
- LAES -0.80 (quantum)
- AVAV -0.78 (defense)
- INTU -0.78 (tech)
- RGTI -0.77 (quantum)

## Dip-in-uptrend (strong long-term, pulling back now)
- **ESTC** — 20d -23.3%, -24.0% off recent high
- **GTLB** — 20d -21.8%, -23.4% off recent high
- **CRWD** — 20d -20.9%, -23.9% off recent high
- **SNOW** — 20d -19.9%, -26.8% off recent high
- **MPC** — 20d -19.5%, -27.6% off recent high
- **VLO** — 20d -16.5%, -29.7% off recent high
- **QLYS** — 20d -15.7%, -16.5% off recent high
- **PSX** — 20d -12.7%, -21.2% off recent high
- **NET** — 20d -12.5%, -20.4% off recent high
- **PANW** — 20d -11.7%, -15.6% off recent high
- **NUE** — 20d -10.9%, -13.1% off recent high
- **TXN** — 20d -9.7%, -11.2% off recent high
