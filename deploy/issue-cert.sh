#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=deploy/common.sh
source "$(dirname "$0")/common.sh"
EMAIL="${CERTBOT_EMAIL:-admin@${DOMAIN}}"
# Fail before issuance if automatic renewal cannot be installed.
bash deploy/install-renewal.sh

docker run --rm \
  -v "$ROOT/deploy/certbot/conf:/etc/letsencrypt" \
  -v "$ROOT/deploy/certbot/www:/var/www/certbot" \
  "$CERTBOT_IMAGE" certonly --webroot -w /var/www/certbot \
  --cert-name "$DOMAIN" -d "$DOMAIN" --email "$EMAIL" \
  --agree-tos --no-eff-email --non-interactive

cp deploy/nginx/ssl.conf.tls deploy/nginx/active/default.conf.template
"${COMPOSE[@]}" up -d --no-deps --force-recreate --wait --wait-timeout 60 nginx
echo "HTTPS enabled for https://${DOMAIN}/; renewal is scheduled twice a day."
