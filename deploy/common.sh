#!/usr/bin/env bash
# Shared setup for production scripts; .env is trusted, shell-compatible server configuration.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${MISISYNC_DEPLOY_LOCKED:-}" != 1 ]]; then
  exec 9>.deploy.lock
  flock -w 1800 9
  export MISISYNC_DEPLOY_LOCKED=1
fi
if [[ ! -f .env ]]; then
  echo 'Missing .env — copy .env.example and configure DOMAIN.' >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a
: "${DOMAIN:?DOMAIN required in .env}"
if [[ ! "$DOMAIN" =~ ^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$ || "$DOMAIN" == *..* ]]; then
  echo 'DOMAIN must be a DNS hostname, without scheme, path or port.' >&2
  exit 1
fi
if [[ -f deploy/release.env ]]; then
  # Locally generated deployment state, retained across git updates.
  # shellcheck disable=SC1091
  source deploy/release.env
  export RELEASE_TAG
fi
mkdir -p deploy/certbot/www deploy/certbot/conf deploy/nginx/active
# Shared with the calling scripts.
# shellcheck disable=SC2034
COMPOSE=(docker compose -f compose.yaml -f compose.prod.yaml)
if [[ "${INTEGRATION_ENABLED:-false}" == true ]]; then
  if [[ ! "${INTEGRATION_PROXY_SECRET:-}" =~ ^[0-9a-f]{64}$ ]]; then
    echo 'Set INTEGRATION_PROXY_SECRET to 64 lowercase hexadecimal characters.' >&2
    exit 1
  fi
  COMPOSE+=(-f compose.integration.yaml)
fi
# The same image is used for issue and renew; set to an official immutable image below.
# shellcheck disable=SC2034
CERTBOT_IMAGE='certbot/certbot@sha256:f70ad0adbb7e117f0fe42a63c553f28ea451edabc0148757b6efcd9735acaa20'
