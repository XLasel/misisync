#!/usr/bin/env bash
# Idempotent per-checkout cron installation; preserves the user's other cron jobs.
set -euo pipefail
# shellcheck source=deploy/common.sh
source "$(dirname "$0")/common.sh"
command -v crontab >/dev/null || { echo 'Install and enable cron first (see deploy/README.md).' >&2; exit 1; }
if command -v systemctl >/dev/null && ! systemctl is-active --quiet cron; then
  echo 'Enable cron first: sudo systemctl enable --now cron' >&2
  exit 1
fi
# Cron treats '%' and newlines specially, even inside shell quotes.
if [[ "$ROOT" == *%* || "$ROOT" == *$'\n'* ]]; then
  echo 'Deployment path must not contain percent signs or newlines.' >&2
  exit 1
fi
umask 077
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT
if ! LC_ALL=C crontab -l > "$TEMP_DIR/current" 2> "$TEMP_DIR/error"; then
  if ! grep -q 'no crontab for' "$TEMP_DIR/error"; then
    cat "$TEMP_DIR/error" >&2
    exit 1
  fi
fi
MARKER="misisync-renew-$(printf '%s' "$ROOT" | sha256sum | cut -c1-12)"
grep -vF "# $MARKER" "$TEMP_DIR/current" > "$TEMP_DIR/new" || true
# Single quotes work with cron's /bin/sh, including a checkout path containing spaces.
QUOTED_ROOT="${ROOT//\'/\'\\\'\'}"
printf "17 */12 * * * /bin/bash '%s/deploy/renew-cert.sh' >> '%s/deploy/certbot/renew.log' 2>&1 # %s\n" \
  "$QUOTED_ROOT" "$QUOTED_ROOT" "$MARKER" >> "$TEMP_DIR/new"
crontab "$TEMP_DIR/new"
echo 'Certificate renewal cron installed (twice a day).'
