# FNCBOT Decisions — 2026-11-25

_Model output, not advice. Data through 2026-11-25; 243 names. Paper/research signals for review — not auto-executed._

## News tilt (reliability-weighted consensus, news weight 0.30)
Net direction per theme = each outlet's call (up/down × strength) weighted by how reliable that outlet has been on that theme.

| Theme | Net tilt | Applied (×0.30) |
|-------|---------:|----------------:|
| ai | -0.04 | -0.012 |
| financials | -0.03 | -0.009 |
| energy | +0.03 | +0.008 |
| defense | +0.02 | +0.006 |
| semis | +0.00 | +0.000 |
| materials | +0.00 | +0.000 |

**Headlines (outlet → calls):**
- Houthis claim drone strike on Saudi Aramco's Ras Tanura refinery/export terminal; satellite imagery shows large fire, oil loadings suspended, Brent tops $93 — _energy, defense_ (cnn.com)
- Treasury (Bessent) sanctions two dozen+ Iranian 'shadow banking' exchange houses/front companies tied to UAE, Turkey, Hong Kong; warns Singapore and Malaysia on secondary sanctions risk as Tehran threatens tanker traffic through Strait of Hormuz — _energy, defense, financials_ (benzinga.com)
- US Commerce/BIS adds Singapore, Malaysia, Indonesia, Thailand and Brazil to 'unacceptable risk of diversion' list, requiring licenses for advanced AI chip shipments there, to block Chinese remote access to Nvidia GPUs amid Megaspeed diversion scandal — _semis, ai_ (aljazeera.com)
- China's Ministry of Commerce extends suspension of expanded rare-earth/lithium-battery export controls from Nov 10 to Jan 10 2027, easing near-term scarcity premium for Western rare-earth producers even as April-2025 curbs on heavy rare earths stay in force — _materials_ (spglobal.com)
- US stock indexes slid in mid-November on worries the AI capex boom may be peaking, even as Anthropic's stock debut drew strong demand; futures markets lean toward a December Fed rate hike (not a cut) as inflation stays elevated under new Chair Warsh — _ai, financials_ (finance.yahoo.com)
- US-mediated Russia-Ukraine peace talks (Abu Dhabi round) remain stalled over territory and security guarantees, with no date set for a next round, keeping geopolitical risk premium elevated — _defense_ (pbs.org)

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
| 1 | **PANW** | +0.63 | +0.63 | +0.00 | tech,cyber |
| 2 | **TGT** | +0.63 | +0.63 | +0.00 | industrial_consumer |
| 3 | **SAIC** | +0.62 | +0.62 | +0.02 | defense |
| 4 | **OKTA** | +0.62 | +0.62 | +0.00 | cyber |
| 5 | **TENB** | +0.61 | +0.61 | +0.00 | cyber |
| 6 | **VRNS** | +0.61 | +0.61 | +0.00 | cyber |
| 7 | **MPC** | +0.60 | +0.59 | +0.03 | energy |
| 8 | **CRWD** | +0.60 | +0.60 | +0.00 | cyber |
| 9 | **PSX** | +0.59 | +0.58 | +0.03 | energy |
| 10 | **VLO** | +0.59 | +0.58 | +0.03 | energy |
| 11 | **S** | +0.58 | +0.58 | +0.00 | cyber |
| 12 | **MRNA** | +0.57 | +0.57 | +0.00 | healthcare |
| 13 | **AMD** | +0.56 | +0.56 | +0.00 | ai,semis |
| 14 | **QLYS** | +0.56 | +0.56 | +0.00 | cyber |
| 15 | **FTNT** | +0.56 | +0.56 | +0.00 | cyber |

## Bottom 8 — likely DOWN
- SOUN -0.81 (ai)
- BBAI -0.81 (ai)
- JOBY -0.80 (space)
- LAES -0.80 (quantum)
- AVAV -0.78 (defense)
- RGTI -0.78 (quantum)
- QBTS -0.77 (quantum)
- INDI -0.77 (semis)

## Dip-in-uptrend (strong long-term, pulling back now)
- **GTLB** — 20d -22.2%, -22.2% off recent high
- **ESTC** — 20d -22.1%, -22.1% off recent high
- **CRWD** — 20d -21.5%, -24.9% off recent high
- **MPC** — 20d -21.2%, -28.4% off recent high
- **SNOW** — 20d -21.2%, -27.5% off recent high
- **VLO** — 20d -16.6%, -29.5% off recent high
- **PSX** — 20d -13.3%, -20.2% off recent high
- **TXN** — 20d -12.4%, -13.6% off recent high
- **NET** — 20d -11.1%, -21.5% off recent high
- **PANW** — 20d -9.7%, -15.2% off recent high
- **COP** — 20d -8.8%, -11.8% off recent high
- **NUE** — 20d -8.6%, -10.6% off recent high
