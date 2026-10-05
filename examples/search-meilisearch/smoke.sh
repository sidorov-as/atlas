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

base_url=${ATLAS_BASE_URL:-http://localhost:${ATLAS_PORT:-18100}}
admin_username=${ATLAS_BOOTSTRAP_USERNAME:-search-admin}
admin_password=${ATLAS_BOOTSTRAP_PASSWORD:?copy .env.example to .env}
group=${ATLAS_BOOTSTRAP_GROUP:-search-platform}

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

csrf() {
  awk '$6 == "csrftoken" {value=$7} END {print value}' "$cookies"
}

expect_status 200 --cookie-jar "$cookies" "$base_url/auth/browser/v1/config"
expect_status 200 \
  --cookie "$cookies" --cookie-jar "$cookies" \
  --header "Origin: $base_url" --header "X-CSRFToken: $(csrf)" \
  --data-urlencode username="$admin_username" \
  --data-urlencode password="$admin_password" \
  "$base_url/auth/browser/v1/providers/atlas.auth.local/credentials"

# A fresh name per run keeps the script rerunnable against the same stack.
system_name="zebracorn-ledger-$(date +%s)"
expect_status 201 \
  --cookie "$cookies" --cookie-jar "$cookies" \
  --header "Origin: $base_url" --header "X-CSRFToken: $(csrf)" \
  --header 'Content-Type: application/json' \
  --data "{\"metadata\":{\"name\":\"$system_name\"},\"spec\":{\"owner\":\"group:$group\"}}" \
  "$base_url/api/systems/"

# Fill the new, empty engine now instead of waiting for the scheduler. The
# scheduler may be running its own first build; reindex then refuses to run
# concurrently, so retry until it gets the lock.
attempt=0
until compose exec -T backend python manage.py reindex; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 15 ]; then
    echo "Search index could not be built." >&2
    exit 1
  fi
  sleep 2
done

expect_status 200 --cookie "$cookies" \
  "$base_url/api/plugins/atlas.search/search/?q=zebracorn"
grep -q "$system_name" "$body"

# Typo tolerance is what Meilisearch adds over the PostgreSQL engine.
expect_status 200 --cookie "$cookies" \
  "$base_url/api/plugins/atlas.search/search/?q=zebracron"
grep -q "$system_name" "$body"

expect_status 200 --cookie "$cookies" "$base_url/api/plugins/atlas.search/status/"
grep -q '"engine":[[:space:]]*"meilisearch"' "$body"

echo "Meilisearch search example smoke test passed."
