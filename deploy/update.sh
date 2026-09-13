#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=deploy/common.sh
source "$(dirname "$0")/common.sh"

PREVIOUS_TAG="${RELEASE_TAG:-}"
export RELEASE_TAG="${1:-${RELEASE_TAG:-}}"
if [[ ! "$RELEASE_TAG" =~ ^[0-9a-f]{40}$ ]]; then
  echo 'Pass a published 40-character commit SHA on the first deployment.' >&2
  exit 1
fi
# Download everything before changing running services or configuration.
"${COMPOSE[@]}" pull

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

"${COMPOSE[@]}" up --no-build -d --remove-orphans --wait --wait-timeout 180
# Refresh nginx's resolved upstream IP after frontend recreation.
"${COMPOSE[@]}" up -d --no-deps --force-recreate --wait --wait-timeout 60 nginx
if [[ "$PREVIOUS_TAG" != "$RELEASE_TAG" && -n "$PREVIOUS_TAG" ]]; then
  printf 'RELEASE_TAG=%s\n' "$PREVIOUS_TAG" > deploy/previous-release.env
fi
printf 'RELEASE_TAG=%s\n' "$RELEASE_TAG" > deploy/release.env.tmp
mv deploy/release.env.tmp deploy/release.env
# Retain current and previous release; never prune unrelated images or volumes.
KEEP_PREVIOUS="$PREVIOUS_TAG"
if [[ -f deploy/previous-release.env ]]; then
  KEEP_PREVIOUS=$(sed -n 's/^RELEASE_TAG=//p' deploy/previous-release.env)
fi
for service in backend frontend; do
  repository="ghcr.io/xlasel/misisync-$service"
  while IFS= read -r tag; do
    if [[ "$tag" =~ ^[0-9a-f]{40}$ && "$tag" != "$RELEASE_TAG" && "$tag" != "$KEEP_PREVIOUS" ]]; then
      docker image rm "$repository:$tag" || echo "Could not remove old image $repository:$tag" >&2
    fi
  done < <(docker image ls "$repository" --format '{{.Tag}}')
done
if [[ "${INTEGRATION_ENABLED:-false}" == true ]]; then
  "${COMPOSE[@]}" up -d --no-deps --force-recreate --wait --wait-timeout 60 integration
fi
echo "OK — ${PUBLIC_URL}"
