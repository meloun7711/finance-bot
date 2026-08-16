#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Run this on YOUR Mac. It SSHes into your EC2 box and sets up FNCBOT there.
# Your key + secrets are used locally and sent straight to your server — they are
# NOT sent to Claude/anyone else. Claude only wrote this script.
#
# Usage (fill in your real values):
#   IP=3.129.206.111 \
#   GITHUB_PAT=xxx \
#   APCA_API_KEY_ID=xxx \
#   APCA_API_SECRET_KEY=xxx \
#   bash deploy/remote_setup.sh
#
# Optional overrides: PEM=~/Downloads/fnc.pem  SSH_USER=ubuntu
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
: "${IP:?set IP=<instance public ip>}"
: "${GITHUB_PAT:?set GITHUB_PAT}"
: "${APCA_API_KEY_ID:?set APCA_API_KEY_ID}"
: "${APCA_API_SECRET_KEY:?set APCA_API_SECRET_KEY}"
PEM="${PEM:-$HOME/Downloads/fnc.pem}"
SSH_USER="${SSH_USER:-ubuntu}"

chmod 400 "$PEM" 2>/dev/null || true

# Repo is private, so raw.githubusercontent.com 404s without auth — clone with the
# PAT first, then run the setup script from the clone.
REMOTE="export GITHUB_PAT='${GITHUB_PAT}' APCA_API_KEY_ID='${APCA_API_KEY_ID}' APCA_API_SECRET_KEY='${APCA_API_SECRET_KEY}'; \
  sudo apt-get update -y && sudo apt-get install -y git python3-pip; \
  git clone https://\$GITHUB_PAT@github.com/meloun7711/finance-bot.git ~/finance-bot 2>/dev/null || true; \
  cd ~/finance-bot && bash deploy/aws_setup.sh \
  && echo '--- first live run ---' && ~/finance-bot/run_daily.sh"

echo "Connecting to ${SSH_USER}@${IP} …"
ssh -i "$PEM" -o StrictHostKeyChecking=accept-new "${SSH_USER}@${IP}" "$REMOTE"
echo
echo "Done. If you saw a 'FNCBOT cycle' push above, your always-on bot is live."
echo "If SSH failed with 'ubuntu' try:  SSH_USER=ec2-user IP=$IP GITHUB_PAT=... bash deploy/remote_setup.sh"
