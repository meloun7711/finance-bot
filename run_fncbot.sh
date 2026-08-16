#!/bin/bash
# FNCBOT daily driver — local scheduled run (launchd fires this each weekday).
# PAPER only: simulated money, no real orders. Refresh data, run one cycle, log.
cd "/Users/meloun7711/Finance bot" || exit 1
PY="/Users/meloun7711/miniconda3/bin/python3"
LOG="FNCBOT/cron.log"
mkdir -p FNCBOT
{
  echo "===================== $(date) ====================="
  "$PY" -m finance_bot.cli download --fast 2>&1 | tail -2
  "$PY" -m finance_bot.cli fncbot --run 2>&1
  echo
} >> "$LOG" 2>&1
