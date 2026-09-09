#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=deploy/common.sh
source "$(dirname "$0")/common.sh"

CERT_DIR="deploy/certbot/conf/live/${DOMAIN}"
if [[ -f "${CERT_DIR}/fullchain.pem" && -f "${CERT_DIR}/privkey.pem" ]]; then
  echo 'Using HTTPS nginx configuration.'
  cp deploy/nginx/ssl.conf.tls deploy/nginx/active/default.conf.template
  PUBLIC_URL="https://${DOMAIN}/"
  # Install before changing containers: a missing cron service must not go unnoticed.
  bash deploy/install-renewal.sh
else
  echo 'No certificate found; using HTTP nginx configuration.'
  cp deploy/nginx/http.conf.template deploy/nginx/active/default.conf.template
  PUBLIC_URL="http://${DOMAIN}/"
fi

"${COMPOSE[@]}" up --build -d --remove-orphans --wait --wait-timeout 180
# Refresh nginx's resolved upstream IP after frontend recreation.
"${COMPOSE[@]}" up -d --no-deps --force-recreate --wait --wait-timeout 60 nginx
echo "OK — ${PUBLIC_URL}"
