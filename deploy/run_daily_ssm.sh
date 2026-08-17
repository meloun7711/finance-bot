#!/usr/bin/env bash
# FNCBOT daily runner — SSM edition. Secrets live in AWS SSM Parameter Store
# (SecureString) and are fetched at runtime via the instance's IAM role, so no
# credential is ever stored on disk or passed through anyone. PAPER only.
set -e
REGION="${AWS_REGION:-us-east-2}"
get(){ aws ssm get-parameter --name "$1" --with-decryption --query Parameter.Value --output text --region "$REGION"; }

export APCA_API_KEY_ID="$(get /fncbot/apca_key_id)"
export APCA_API_SECRET_KEY="$(get /fncbot/apca_secret)"
GH_PAT="$(get /fncbot/github_pat)"

cd "$HOME/finance-bot"
git remote set-url origin "https://${GH_PAT}@github.com/meloun7711/finance-bot.git"
git fetch origin fncbot-state && git checkout fncbot-state && git pull --ff-only origin fncbot-state || true

python3 -m finance_bot.cli download --source alpaca
python3 -m finance_bot.cli export-market
python3 -m finance_bot.cli fncbot --run

git add FNCBOT market
git -c user.name=FNCBOT -c user.email=noreply@anthropic.com commit -m "FNCBOT cycle $(date -u +%F)" || true
git push origin fncbot-state
