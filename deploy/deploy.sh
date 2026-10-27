#!/usr/bin/env bash
#
# Deploy origin/main if it changed since the last successful deploy.
# Run every minute by interactivestories-deploy.timer (see deploy/README.md).
# Set FORCE=1 to redeploy even when nothing changed.

set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
BRANCH="${BRANCH:-main}"
SERVICE="${SERVICE:-interactivestories}"
UV="${UV:-$(command -v uv || echo "$HOME/.local/bin/uv")}"

cd "$APP_DIR"

DB="instance/stories.db"
STATE="instance/.deployed-commit"

git fetch --quiet origin "$BRANCH"
TARGET="$(git rev-parse "origin/$BRANCH")"

if [ "${FORCE:-}" != "1" ] && [ -f "$STATE" ] && [ "$(cat "$STATE")" = "$TARGET" ]; then
    exit 0
fi

echo "Deploying ${TARGET:0:7} ..."

# Keep the live database even if git would delete or replace it
# (it used to be tracked, so the first deploy after untracking it would remove it)
DB_COPY=""
if [ -f "$DB" ]; then
    DB_COPY="$(mktemp)"
    cp "$DB" "$DB_COPY"
fi

# .env, instance/ and uploads/ are git-ignored, so reset leaves them alone
git reset --hard --quiet "$TARGET"

if [ -n "$DB_COPY" ]; then
    mkdir -p instance
    cp "$DB_COPY" "$DB"
    rm -f "$DB_COPY"
fi

"$UV" sync --frozen

sudo -n systemctl restart "$SERVICE"
sleep 5

if ! systemctl is-active --quiet "$SERVICE"; then
    echo "❌ $SERVICE is not running after deploy" >&2
    journalctl -u "$SERVICE" -n 30 --no-pager >&2 || true
    exit 1
fi

mkdir -p instance
echo "$TARGET" > "$STATE"
echo "✅ Deployed ${TARGET:0:7}"
