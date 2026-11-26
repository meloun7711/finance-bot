# FNCBOT Decisions — 2026-11-25

_Model output, not advice. Data through 2026-11-25; 243 names. Paper/research signals for review — not auto-executed._

## News tilt (reliability-weighted consensus, news weight 0.30)
Net direction per theme = each outlet's call (up/down × strength) weighted by how reliable that outlet has been on that theme.

| Theme | Net tilt | Applied (×0.30) |
|-------|---------:|----------------:|
| energy | +0.00 | +0.000 |
| semis | +0.00 | +0.000 |
| ai | +0.00 | +0.000 |
| defense | +0.00 | +0.000 |
| financials | +0.00 | +0.000 |

**Headlines (outlet → calls):**
- Oil prices rally as Middle East supply fears return ahead of Nov 29 OPEC+ meeting (Ras Tanura attack reported, Brent ~$94.50) — _energy_ (finscans.com)
- Nvidia halts AI chip server shipments to Malaysia, Singapore, Thailand and Indonesia amid US export crackdown on compute-rental bypass routes — _semis, ai_ (thenationalnews.com)
- Dow, S&P 500, Nasdaq futures fall after Treasury Secretary Bessent unveils fresh Iran sanctions and Strait of Hormuz warnings — _defense, energy_ (benzinga.com)
- Traders raise bets on a December Fed rate hike as inflation stays elevated; Dow/S&P/Nasdaq futures slip — _financials_ (tradingview.com)
- Russia-Ukraine peace talks stall after Abu Dhabi round; Kremlin sets no date for next round, rouble and Russian stocks fall — _defense_ (newsweek.com)

**Outlet reliability (learned, per theme):**
- ajc.com (overall 0.31): financials 0.20
- aljazeera.com (overall 0.31): defense 0.30, energy 0.24
- apnews.com (overall 0.39): financials 0.30
- cbsnews.com (overall 0.50): defense 0.55, energy 0.50
- cfr.org (overall 0.39): defense 0.30
- cnbc.com (overall 0.80): semis 0.84, ai 0.82, financials 0.82
- cnn.com (overall 0.69): semis 0.76, ai 0.70
- datacenterknowledge.com (overall 0.31): ai 0.30, semis 0.24
- digitimes.com (overall 0.61): semis 0.70
- finance.yahoo.com (overall 0.58): semis 0.60, ai 0.54
- finance.yahoo.com (reuters) (overall 0.74): tech 0.80, ai 0.76, semis 0.70
- fool.com (overall 0.66): materials 0.76
- gcaptain.com (overall 0.31): defense 0.30, energy 0.24
- globalcompetitionreview.com (overall 0.61): tech 0.70
- home.saxo (overall 0.15): tech 0.12, ai 0.11, semis 0.10, energy 0.09
- investinglive.com (overall 0.39): energy 0.30
- khaleejtimes.com (overall 0.50): energy 0.50
- lloydslist.com (overall 0.31): defense 0.30, energy 0.24
- mining.com (overall 0.31): materials 0.20
- news.metal.com (smm) (overall 0.31): materials 0.20
- newsonair.gov.in (overall 0.69): semis 0.76, ai 0.70
- pandaforecast.com / grafa.com / sabq.org (overall 0.36): defense 0.41, energy 0.16
- regfollower.com (overall 0.56): materials 0.62
- spglobal.com (overall 0.50): materials 0.50
- stocktitan.net (overall 0.50): financials 0.50
- thenationalnews.com (overall 0.39): materials 0.30
- zacks.com / foxcarolina.com (overall 0.50): tech 0.50, semis 0.46, ai 0.41

## Top 15 — likely UP (news-adjusted)
| # | Ticker | Decision | Structural | News | Themes |
|---|--------|---------:|-----------:|-----:|--------|
| 1 | **TGT** | +0.63 | +0.63 | +0.00 | industrial_consumer |
| 2 | **PANW** | +0.62 | +0.62 | +0.00 | tech,cyber |
| 3 | **OKTA** | +0.61 | +0.61 | +0.00 | cyber |
| 4 | **SAIC** | +0.61 | +0.61 | +0.00 | defense |
| 5 | **VRNS** | +0.60 | +0.60 | +0.00 | cyber |
| 6 | **TENB** | +0.60 | +0.60 | +0.00 | cyber |
| 7 | **MPC** | +0.59 | +0.59 | +0.00 | energy |
| 8 | **CRWD** | +0.59 | +0.59 | +0.00 | cyber |
| 9 | **VLO** | +0.58 | +0.58 | +0.00 | energy |
| 10 | **PSX** | +0.58 | +0.58 | +0.00 | energy |
| 11 | **MRNA** | +0.57 | +0.57 | +0.00 | healthcare |
| 12 | **S** | +0.57 | +0.57 | +0.00 | cyber |
| 13 | **DELL** | +0.56 | +0.56 | +0.00 | ai |
| 14 | **AMD** | +0.55 | +0.55 | +0.00 | ai,semis |
| 15 | **FTNT** | +0.54 | +0.54 | +0.00 | cyber |

## Bottom 8 — likely DOWN
- JOBY -0.80 (space)
- SOUN -0.80 (ai)
- BBAI -0.80 (ai)
- LAES -0.80 (quantum)
- AVAV -0.78 (defense)
- RGTI -0.78 (quantum)
- INDI -0.77 (semis)
- QBTS -0.77 (quantum)

## Dip-in-uptrend (strong long-term, pulling back now)
- **GTLB** — 20d -24.6%, -24.6% off recent high
- **CRWD** — 20d -23.9%, -27.2% off recent high
- **MPC** — 20d -21.8%, -28.9% off recent high
- **PSX** — 20d -14.8%, -21.6% off recent high
- **OKTA** — 20d -14.4%, -18.0% off recent high
- **NET** — 20d -14.4%, -24.4% off recent high
- **PANW** — 20d -12.5%, -17.9% off recent high
- **NUE** — 20d -11.5%, -13.5% off recent high
- **S** — 20d -9.4%, -11.7% off recent high
- **SWKS** — 20d -8.9%, -13.2% off recent high
- **COP** — 20d -8.7%, -11.6% off recent high
- **EOG** — 20d -8.5%, -11.1% off recent high
