#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=deploy/common.sh
source "$(dirname "$0")/common.sh"

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --dry-run ) ]]; then
  echo 'Usage: renew-cert.sh [--dry-run]' >&2
  exit 1
fi
# Persist the reload marker so a failed nginx reload is retried even on a no-op renewal.
STAMP="$ROOT/deploy/certbot/www/.reload-required"
result=0
docker run --rm \
  -v "$ROOT/deploy/certbot/conf:/etc/letsencrypt" \
  -v "$ROOT/deploy/certbot/www:/var/www/certbot" \
  "$CERTBOT_IMAGE" renew --cert-name "$DOMAIN" --webroot -w /var/www/certbot \
  --non-interactive --quiet --deploy-hook 'touch /var/www/certbot/.reload-required' \
  "$@" || result=$?

if [[ -e "$STAMP" && "${1:-}" != --dry-run ]]; then
  "${COMPOSE[@]}" exec -T nginx nginx -t
  "${COMPOSE[@]}" exec -T nginx nginx -s reload
  if [[ "${INTEGRATION_ENABLED:-false}" == true ]]; then
    "${COMPOSE[@]}" exec -T integration nginx -t
    "${COMPOSE[@]}" exec -T integration nginx -s reload
  fi
  rm -f "$STAMP"
fi
exit "$result"
