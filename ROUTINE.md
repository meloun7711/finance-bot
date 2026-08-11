# FNCBOT Routine — one call a day (09:30 ET)

A self-sufficient prompt for a scheduled agent. It runs **once per trading day at
market open**. One call does everything: settle yesterday, (maybe) learn, and
trade today's book. All state, learning history, and version control live under
**`./FNCBOT/`**. The money math, fees, and adaptation are done deterministically
by `finance_bot.fncbot` — the agent only refreshes data, runs the cycle, and reports.

> **PAPER ONLY.** Simulated money. No real orders, no brokerage credentials, no funds.

---

## How to schedule it
One trigger, US trading days, **09:35 America/New_York** (a few minutes after the
09:30 open so today's opening bar exists). The engine self-guards against
double-runs and non-trading days (weekends/holidays), so an extra trigger is harmless.

---

## THE ROUTINE PROMPT  (paste this as the scheduled task)

```
You operate FNCBOT, a PAPER (simulated) trading bot at /Users/meloun7711/Finance bot.
Simulated money only — NEVER place a real order, use real credentials, or move funds.
Run today's single cycle and report. Do exactly this:

1. REFRESH DATA:
   Run:  python -m finance_bot.cli download --force
   If it fails or returns no data, STOP and report "data refresh failed — no action
   taken." Take no trading action.

2. RUN THE DAILY CYCLE:
   Run:  python -m finance_bot.cli fncbot --run
   (This settles yesterday's close, runs the learner if due, and trades today's
   book at the open. Never pass --reset.)

3. READ the JSON it prints and REPORT a concise summary:
   - date, model_version, and whether "learned" is non-null
     (if so, say what changed and why — this is a strategy version change).
   - trades made, fees charged today, portfolio value, cash, # positions,
     and cumulative return %.
   If the JSON has "skipped" (already ran today / non-trading day) or "error",
   report that and stop. On "error", take NO trading action and do not retry.

4. If a version change or revert happened, note it clearly so it can be reviewed
   against performance later (the full history is in FNCBOT/changelog.jsonl).

Rules you must not break:
- PAPER ONLY. Never place real orders or use real credentials.
- Never pass --reset (it wipes the account) unless a human explicitly says so.
- The 5%-per-position cap, fee model, and parameter bounds are enforced in code —
  never override them. This is model output, not investment advice.
```

---

## What the one daily cycle does
| Step | What happens |
|------|--------------|
| **1. Settle** | Mark the book to **yesterday's close**, append equity + daily P&L to `FNCBOT/performance.csv` (tagged with the active model version). |
| **2. Learn** *(every ~5 sessions)* | Evaluate the live version. Within hard bounds, adjust **one** knob (exposure), or **revert** the last change if its daily P&L was worse than its parent version. Every change → a new version, logged. |
| **3. Trade** | Rebalance to the signal's target book (top-N ≥ gate, ≤5%/name × exposure), filling at **today's open** with fees + slippage. Leak-safe: decision uses only data ≤ yesterday's close. |

## Self-learning — what it is (and isn't)
It is a **bounded, reversible controller**, not a black box:
- **Learnable knobs:** `exposure` (0.5–1.0), `gate` (0.25–0.45), `max_positions` (10–25). The 5%/name cap is never exceeded.
- **Adapts to its own drawdown:** deep drawdown → cut exposure (de-risk); calm & positive → restore it.
- **Auto-rollback:** a version whose daily P&L underperforms its parent is reverted automatically, and the revert is logged.
- It is **not guaranteed to improve returns** — adapting to your own P&L can curve-fit. The version log exists precisely so you can *see* whether a change helped or hurt.

## Version control & audit (`./FNCBOT/`)
| File | Contents |
|------|----------|
| `model.json` | current version + params (`gate`, `max_positions`, `exposure`). |
| `versions/vN.json` | immutable snapshot of every version. |
| `changelog.jsonl` | every change: version, event (create/adjust/revert), what changed, **why**, and the performance snapshot that triggered it. |
| `performance.csv` | daily equity **tagged with the active version** → attribute P&L to each version. |
| `trades.csv` | every fill: side, shares, ref/fill price, each fee component, cash after. |
| `account.json` | cash, positions (shares + avg cost), running totals (fees, realized P&L). |

**To see if a change helped or hurt:** group `performance.csv` by `version` and
compare `daily_pnl` / drawdown across versions; cross-reference `changelog.jsonl`
for the reason behind each change. (A 45-session replay produced 7 versions with
2 automatic rollbacks — the mechanism is proven.)

## Fee model (real 2026 US-equity costs, commission-free broker)
Sells: SEC $20.60/$1M + FINRA TAF $0.000195/sh (min $0.01, cap $9.79). Buys: $0
regulatory. Slippage: 1 bp/side in the fill price. Edit at the top of
`finance_bot/paper.py`.

## Manual controls (human only, not the routine)
```bash
python -m finance_bot.cli fncbot                     # status snapshot
python -m finance_bot.cli fncbot --run               # run one cycle by hand
python -m finance_bot.cli fncbot --reset --capital 100000   # start fresh at v1
```

## Safety
Simulated only — the engine cannot connect to a broker; no real orders, no
credentials, no fund movement. Signals and adaptations are model output, not
investment advice.
