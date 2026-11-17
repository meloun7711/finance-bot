# FNCBOT Decisions — 2026-11-16

_Model output, not advice. Data through 2026-11-16; 243 names. Paper/research signals for review — not auto-executed._

## News tilt (reliability-weighted consensus, news weight 0.30)
Net direction per theme = each outlet's call (up/down × strength) weighted by how reliable that outlet has been on that theme.

| Theme | Net tilt | Applied (×0.30) |
|-------|---------:|----------------:|
| defense | +0.08 | +0.023 |
| energy | +0.08 | +0.023 |
| materials | -0.03 | -0.009 |
| ai | +0.00 | +0.000 |
| semis | +0.00 | +0.000 |
| financials | +0.00 | +0.000 |

**Headlines (outlet → calls):**
- Nvidia CEO Jensen Huang resigned amid a personal-conduct controversy; CFO Colette Kress is interim CEO, stock down ~35% from its October peak (worst since June 2025), at least 10 analysts cut to Hold citing no clear successor; Q3 FY2027 earnings due after close today — _ai down/strong, semis down/strong_ (finance.yahoo.com)
- CBS News: Iranian claims of tankers striking mines near Strait of Hormuz are largely unverified/disputed (CENTCOM called one claim 'FALSE', Trump accuses Iran of fabricating to raise oil prices); UKMTO independently confirms separate projectile strikes on tankers continue, and the US naval blockade on Iranian oil ports remains in place — _defense up/moderate, energy up/moderate_ (cbsnews.com)
- China's rare-earth export-control pause (covering holmium, erbium, thulium, europium, ytterbium and related processing tech) was set to expire Nov 10; as of early Nov it had not yet been formally re-extended, leaving legal status of the suspension uncertain even as other reporting claims a Jan 10, 2027 extension was announced — _materials down/mild_ (fool.com)
- CNBC: St. Louis Fed's Musalem says the Fed may need up to four more rate hikes; Chicago Fed's Goolsbee called October's hotter-than-expected CPI 'borderline disturbing'; CME FedWatch shows fed funds futures unanimously pricing a December hike after October's hold (two governors dissented in favor of hiking then) — _financials down/moderate_ (cnbc.com)

**Outlet reliability (learned, per theme):**
- ajc.com (overall 0.31): financials 0.20
- cbsnews.com (overall 0.69): defense 0.76, energy 0.70
- cnbc.com (overall 0.39): financials 0.30
- finance.yahoo.com (reuters) (overall 0.74): tech 0.80, ai 0.76, semis 0.70
- fool.com (overall 0.61): materials 0.70
- home.saxo (overall 0.23): tech 0.30, ai 0.24, semis 0.20, energy 0.17
- mining.com (overall 0.39): materials 0.30
- news.metal.com (smm) (overall 0.31): materials 0.20
- pandaforecast.com / grafa.com / sabq.org (overall 0.36): defense 0.41, energy 0.16
- stocktitan.net (overall 0.39): financials 0.30
- zacks.com / foxcarolina.com (overall 0.50): tech 0.50, semis 0.46, ai 0.41

## Top 15 — likely UP (news-adjusted)
| # | Ticker | Decision | Structural | News | Themes |
|---|--------|---------:|-----------:|-----:|--------|
| 1 | **MPC** | +0.67 | +0.65 | +0.08 | energy |
| 2 | **PSX** | +0.67 | +0.64 | +0.08 | energy |
| 3 | **VLO** | +0.66 | +0.64 | +0.08 | energy |
| 4 | **TRGP** | +0.61 | +0.59 | +0.08 | energy |
| 5 | **TGT** | +0.61 | +0.61 | +0.00 | industrial_consumer |
| 6 | **SAIC** | +0.60 | +0.57 | +0.08 | defense |
| 7 | **OKTA** | +0.59 | +0.59 | +0.00 | cyber |
| 8 | **AMD** | +0.59 | +0.59 | +0.00 | ai,semis |
| 9 | **CRWD** | +0.58 | +0.58 | +0.00 | cyber |
| 10 | **MRNA** | +0.57 | +0.57 | +0.00 | healthcare |
| 11 | **DELL** | +0.57 | +0.57 | +0.00 | ai |
| 12 | **COP** | +0.57 | +0.54 | +0.08 | energy |
| 13 | **NUE** | +0.57 | +0.57 | -0.03 | materials |
| 14 | **PANW** | +0.56 | +0.56 | +0.00 | tech,cyber |
| 15 | **TWLO** | +0.56 | +0.56 | +0.00 | ai |

## Bottom 8 — likely DOWN
- BBAI -0.80 (ai)
- LAES -0.80 (quantum)
- JOBY -0.80 (space)
- SOUN -0.79 (ai)
- RGTI -0.77 (quantum)
- INDI -0.77 (semis)
- QBTS -0.77 (quantum)
- AVAV -0.76 (defense)

## Dip-in-uptrend (strong long-term, pulling back now)
- **VLO** — 20d -14.1%, -19.1% off recent high
- **MPC** — 20d -13.9%, -15.7% off recent high
- **GTLB** — 20d -11.3%, -18.5% off recent high
- **PSX** — 20d -10.1%, -12.1% off recent high
- **SNOW** — 20d -9.5%, -22.6% off recent high
- **PANW** — 20d -8.4%, -24.3% off recent high
- **OXY** — 20d -8.3%, -10.4% off recent high
- **OKTA** — 20d -6.5%, -23.5% off recent high
- **XOM** — 20d -5.4%, -10.0% off recent high
- **AMD** — 20d -5.1%, -21.4% off recent high
- **ADI** — 20d -3.1%, -11.8% off recent high
- **NUE** — 20d -2.9%, -8.7% off recent high
