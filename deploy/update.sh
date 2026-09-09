#!/usr/bin/env bash
# Run on the Timeweb VPS from the app directory after git pull.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.example and set DOMAIN / TRUST_PROXY" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

if [[ -z "${DOMAIN:-}" ]]; then
  echo "DOMAIN must be set in .env for production compose" >&2
  exit 1
fi

mkdir -p deploy/certbot/www deploy/certbot/conf deploy/nginx/active

CERT_DIR="deploy/certbot/conf/live/${DOMAIN}"
if [[ -f "${CERT_DIR}/fullchain.pem" && -f "${CERT_DIR}/privkey.pem" ]]; then
  echo "Using HTTPS nginx configuration."
  cp deploy/nginx/ssl.conf.tls deploy/nginx/active/default.conf.template
  PUBLIC_URL="https://${DOMAIN}/"
else
  echo "No certificate found; using HTTP nginx configuration."
  cp deploy/nginx/http.conf.template deploy/nginx/active/default.conf.template
  PUBLIC_URL="http://${DOMAIN}/"
fi

echo "Building and starting stack (compose.yaml + compose.prod.yaml)..."
docker compose -f compose.yaml -f compose.prod.yaml up --build -d --remove-orphans
docker compose -f compose.yaml -f compose.prod.yaml up -d --no-deps --force-recreate nginx

echo "Waiting for nginx health..."
for _ in $(seq 1 30); do
  if docker compose -f compose.yaml -f compose.prod.yaml exec -T nginx wget -qO- http://127.0.0.1/healthz >/dev/null 2>&1; then
    echo "OK — ${PUBLIC_URL}"
    exit 0
  fi
  sleep 2
done

echo "Stack started but nginx healthcheck did not pass yet; check: docker compose -f compose.yaml -f compose.prod.yaml ps" >&2
exit 1
