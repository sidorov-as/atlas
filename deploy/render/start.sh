#!/usr/bin/env bash
# Entry point of the Render demo container: start the baked PostgreSQL,
# apply the admin password from the environment, then run gunicorn + Caddy.
set -euo pipefail
cd /code/core/backend

# Render exposes the public hostname at runtime; trust it automatically.
if [ -n "${RENDER_EXTERNAL_HOSTNAME:-}" ]; then
  export DJANGO_ALLOWED_HOSTS="${DJANGO_ALLOWED_HOSTS:-localhost},${RENDER_EXTERNAL_HOSTNAME}"
  export DJANGO_CSRF_TRUSTED_ORIGINS="${DJANGO_CSRF_TRUSTED_ORIGINS:+${DJANGO_CSRF_TRUSTED_ORIGINS},}https://${RENDER_EXTERNAL_HOSTNAME}"
fi

pg_ctl start --wait --silent --log=/tmp/postgres.log

# The image is seeded with the default demo password; replace it with the
# one configured on Render (the seed only knows the build-time default).
if [ -n "${ATLAS_DEMO_ADMIN_PASSWORD:-}" ]; then
  python manage.py seed_admin \
    --username "${ATLAS_DEMO_ADMIN_USERNAME:-admin}" \
    --password-env ATLAS_DEMO_ADMIN_PASSWORD
fi

if [ -n "${ATLAS_DEMO_GUEST_PASSWORD:-}" ]; then
  python manage.py seed_guest \
    --username "${ATLAS_DEMO_GUEST_USERNAME:-guest}" \
    --password-env ATLAS_DEMO_GUEST_PASSWORD
fi

gunicorn server.wsgi:application \
  --bind 127.0.0.1:8000 \
  --worker-class gthread \
  --workers "${WEB_CONCURRENCY:-1}" \
  --threads 4 \
  --timeout 120 &
caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &

# Exit (and let Render restart the container) if any process dies.
wait -n
exit 1
