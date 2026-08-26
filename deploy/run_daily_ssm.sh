#!/usr/bin/env bash
# FNCBOT daily runner — SSM edition. Secrets from SSM Parameter Store at runtime.
# PAPER only. Robust to the brain routine pushing the same branch concurrently.
set -uo pipefail
REGION="${AWS_REGION:-us-east-2}"
get(){ aws ssm get-parameter --name "$1" --with-decryption --query Parameter.Value --output text --region "$REGION"; }

export APCA_API_KEY_ID="$(get /fncbot/apca_key_id)"
export APCA_API_SECRET_KEY="$(get /fncbot/apca_secret)"
GH_PAT="$(get /fncbot/github_pat)"

cd "$HOME/finance-bot" || exit 1
git remote set-url origin "https://${GH_PAT}@github.com/meloun7711/finance-bot.git"

# clean-sync to the latest origin (carries the last committed state + the brain's
# decisions/news_tilt); -f discards any leftover local mess so we never get stuck
git fetch origin fncbot-state
git checkout -f -B fncbot-state origin/fncbot-state

python3 -m finance_bot.cli download --source alpaca
python3 -m finance_bot.cli export-market
python3 -m finance_bot.cli trade-paper || true          # Alpaca PAPER orders from predictions
python3 -m finance_bot.cli fncbot --run

git add FNCBOT market
git -c user.name=FNCBOT -c user.email=noreply@anthropic.com commit -m "FNCBOT cycle $(date -u +%F)" || true

# push, rebasing over any brain commit that landed meanwhile; retry a few times
for i in 1 2 3 4 5; do
  git fetch origin fncbot-state
  if git rebase origin/fncbot-state && git push origin fncbot-state; then
    echo "pushed on attempt $i"; break
  fi
  git rebase --abort 2>/dev/null || true
  sleep 3
done
