#!/bin/sh
set -eu

compose_env_file=${ATLAS_COMPOSE_ENV_FILE:-./.env}
if [ ! -f "$compose_env_file" ]; then
  compose_env_file=./.env.example
fi
set -a
# This example owns its env file; loading it makes smoke and Compose agree.
. "$compose_env_file"
set +a

compose() {
  docker compose --env-file "$compose_env_file" "$@"
}

base_url=${ATLAS_BASE_URL:-http://localhost:${ATLAS_PORT:-18080}}
viewer_username=local-example-viewer
viewer_password=${ATLAS_SMOKE_VIEWER_PASSWORD:-}

if [ -z "$viewer_password" ]; then
  echo "ATLAS_SMOKE_VIEWER_PASSWORD is required (copy .env.example to .env)." >&2
  exit 2
fi

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM
cookies="$tmp_dir/cookies.txt"
body="$tmp_dir/body.json"

expect_status() {
  expected=$1
  shift
  actual=$(curl --silent --show-error --output "$body" --write-out '%{http_code}' "$@")
  if [ "$actual" != "$expected" ]; then
    echo "Expected HTTP $expected, received $actual:" >&2
    sed -n '1,80p' "$body" >&2
    exit 1
  fi
}

compose exec -T \
  -e ATLAS_SMOKE_VIEWER_PASSWORD="$viewer_password" \
  backend python manage.py shell -c '
import os
from atlas_plugin_api import KIND_ACTOR, get_catalog_entity_model
from atlas_plugin_standard_catalog.models import ActorDetails
from django.contrib.auth import get_user_model

user, _ = get_user_model().objects.get_or_create(username="local-example-viewer")
user.is_active = True
user.is_staff = False
user.is_superuser = False
user.set_password(os.environ["ATLAS_SMOKE_VIEWER_PASSWORD"])
user.save()
entity, _ = get_catalog_entity_model().objects.get_or_create(
    kind=KIND_ACTOR, name="local-example-viewer",
)
ActorDetails.objects.update_or_create(
    entity=entity,
    defaults={"account": user, "display_name": "Local example viewer"},
)
'

expect_status 200 --cookie-jar "$cookies" "$base_url/auth/browser/v1/config"
csrf_token=$(awk '$6 == "csrftoken" {value=$7} END {print value}' "$cookies")
if [ -z "$csrf_token" ]; then
  echo "Authentication config did not issue a CSRF cookie." >&2
  exit 1
fi

expect_status 403 \
  --cookie "$cookies" --cookie-jar "$cookies" \
  --header "Origin: $base_url" --header "X-CSRFToken: $csrf_token" \
  --header 'Content-Type: application/json' --header 'Accept: application/json' \
  --data '{"username":"signup-must-stay-closed","password":"not-used-local-example-password"}' \
  "$base_url/auth/browser/v1/signup"

expect_status 200 \
  --cookie "$cookies" --cookie-jar "$cookies" \
  --header "Origin: $base_url" --header "X-CSRFToken: $csrf_token" \
  --data-urlencode username="$viewer_username" \
  --data-urlencode password="$viewer_password" \
  "$base_url/auth/browser/v1/providers/atlas.auth.local/credentials"

# Django rotates the CSRF secret on successful login.
csrf_token=$(awk '$6 == "csrftoken" {value=$7} END {print value}' "$cookies")

expect_status 200 --cookie "$cookies" "$base_url/api/me/"
grep -q '"isAdmin":[[:space:]]*false' "$body"

expect_status 403 \
  --cookie "$cookies" --cookie-jar "$cookies" \
  --header "Origin: $base_url" --header "X-CSRFToken: $csrf_token" \
  --header 'Content-Type: application/json' \
  --data '{"metadata":{"name":"smoke-denied-system"},"spec":{"owner":"group:local-platform"}}' \
  "$base_url/api/systems/"

expect_status 204 \
  --request DELETE --cookie "$cookies" --cookie-jar "$cookies" \
  --header "Origin: $base_url" --header "X-CSRFToken: $csrf_token" \
  "$base_url/auth/browser/v1/session"

expect_status 200 --cookie "$cookies" "$base_url/auth/browser/v1/session"
grep -q '"is_authenticated":[[:space:]]*false' "$body"

echo "Local authentication example smoke test passed."
