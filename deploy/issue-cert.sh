#!/usr/bin/env bash
# Issue or renew Let's Encrypt certs, then switch nginx to TLS template.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
set -a
source .env
set +a

: "${DOMAIN:?DOMAIN required}"
EMAIL="${CERTBOT_EMAIL:-admin@${DOMAIN}}"

mkdir -p deploy/certbot/www deploy/certbot/conf

echo "Requesting certificate for ${DOMAIN}..."
docker run --rm \
  -v "$(pwd)/deploy/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/deploy/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d "${DOMAIN}" --email "${EMAIL}" --agree-tos --no-eff-email --non-interactive

echo "Enabling TLS nginx template..."
cp deploy/nginx/ssl.conf.tls deploy/nginx/templates/default.conf.template

docker compose -f compose.yaml -f compose.prod.yaml up -d --force-recreate nginx

echo "HTTPS enabled for https://${DOMAIN}/"
echo "Renew later with: ./deploy/issue-cert.sh  (certbot renew is safe to re-run)"
