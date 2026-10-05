#!/usr/bin/env bash
# Build-time step of deploy/render/Dockerfile: create a local PostgreSQL
# cluster, apply migrations, load the booking demo, build the search index and
# collect static files, so the container starts with a ready catalog and no
# network dependencies.
set -euo pipefail
cd /code/core/backend

# Production settings refuse to import without these; the real values come
# from Render at runtime and nothing here depends on them.
export DJANGO_SECRET_KEY="build-only-$(head -c 48 /dev/urandom | base64 | tr -d '\n/+=')"
export DJANGO_ALLOWED_HOSTS=localhost

initdb --username="$POSTGRES_USER" --auth=trust --encoding=UTF8 --no-instructions >/dev/null
cat >> "$PGDATA/postgresql.conf" <<'CONF'
listen_addresses = '127.0.0.1'
unix_socket_directories = '/tmp'
max_connections = 20
shared_buffers = 32MB
# Throwaway demo data: durability is not needed.
fsync = off
synchronous_commit = off
full_page_writes = off
CONF

pg_ctl start --wait --silent --log=/tmp/postgres-build.log
createdb --host=127.0.0.1 --username="$POSTGRES_USER" "$POSTGRES_DB"

python manage.py migrate --noinput
python manage.py seed_booking_demo --yes
# The demo runs no scheduler, so ship a ready search index: build it right
# after the catalog is seeded.
python manage.py reindex
python manage.py collectstatic --noinput

pg_ctl stop --wait --silent --mode=fast
