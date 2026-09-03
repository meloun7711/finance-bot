#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# FNCBOT — one-time setup on a fresh Ubuntu EC2 instance (Variant A: the box runs
# the whole PAPER bot daily and pushes state to the repo). Unrestricted network,
# so Alpaca works with no proxy. PAPER only — no real orders, ever.
#
# YOU PROVIDE (as env vars, before running this script):
#   GITHUB_PAT            fine-grained GitHub PAT, contents:read+write on the repo
#   APCA_API_KEY_ID       Alpaca (paper) data key id
#   APCA_API_SECRET_KEY   Alpaca (paper) data secret
#
# Run:  GITHUB_PAT=... APCA_API_KEY_ID=... APCA_API_SECRET_KEY=... bash aws_setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
: "${GITHUB_PAT:?set GITHUB_PAT}"; : "${APCA_API_KEY_ID:?set APCA_API_KEY_ID}"; : "${APCA_API_SECRET_KEY:?set APCA_API_SECRET_KEY}"

REPO_PATH="meloun7711/finance-bot"
DIR="$HOME/finance-bot"

sudo apt-get update -y && sudo apt-get install -y python3-pip git

# clone (or update) using the PAT; persist creds so cron can push unattended
if [ ! -d "$DIR/.git" ]; then
  git clone "https://${GITHUB_PAT}@github.com/${REPO_PATH}.git" "$DIR"
fi
cd "$DIR"
git remote set-url origin "https://${GITHUB_PAT}@github.com/${REPO_PATH}.git"
pip3 install --quiet -r requirements.txt

# secrets live in a 0600 env file, sourced by the daily runner (not in cron/args)
cat > "$HOME/.fncbot.env" <<EOF
export APCA_API_KEY_ID='${APCA_API_KEY_ID}'
export APCA_API_SECRET_KEY='${APCA_API_SECRET_KEY}'
EOF
chmod 600 "$HOME/.fncbot.env"

# the daily runner: sync state branch, refresh via Alpaca, run cycle, push state
cat > "$DIR/run_daily.sh" <<'EOF'
#!/usr/bin/env bash
set -e
source "$HOME/.fncbot.env"
cd "$HOME/finance-bot"
git fetch origin fncbot-state && git checkout fncbot-state && git pull --ff-only origin fncbot-state || true
python3 -m finance_bot.cli download --source alpaca
python3 -m finance_bot.cli fncbot --run
git add FNCBOT
git -c user.name=FNCBOT -c user.email=noreply@anthropic.com commit -m "FNCBOT cycle $(date -u +%F)" || true
git push origin fncbot-state
EOF
chmod +x "$DIR/run_daily.sh"

# cron: weekdays 14:35 UTC (9:35 EST / 10:35 EDT — always just after the US open)
( crontab -l 2>/dev/null | grep -v run_daily.sh; \
  echo "35 14 * * 1-5 bash $DIR/run_daily.sh >> $DIR/FNCBOT/cron.log 2>&1" ) | crontab -

echo "✓ Setup complete. Test it now with:  $DIR/run_daily.sh"
echo "  Logs will be at: $DIR/FNCBOT/cron.log ; state pushes to the fncbot-state branch."
