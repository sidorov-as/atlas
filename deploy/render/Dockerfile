# syntax=docker/dockerfile:1
#
# Self-contained image for the public demo on Render's free plan (see
# render.yaml). Everything runs in one container:
#   - PostgreSQL on 127.0.0.1, with the booking demo already migrated and
#     seeded at build time into the image;
#   - gunicorn on 127.0.0.1:8000;
#   - Caddy on $PORT serving the SPA and static files and proxying the backend.
# The container filesystem is ephemeral, so every restart (nightly via
# .github/workflows/render-demo-reset.yml, or Render's idle spin-down) brings
# back the pristine demo catalog.
#
# The Python part mirrors core/backend/Dockerfile — keep them in sync, except
# that there is no local PlantUML (see selected_plugins.py below).

FROM node:22-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
COPY core/frontend/package.json core/frontend/package.json
COPY plugin-api/typescript/package.json plugin-api/typescript/package.json
COPY plugins/standard-catalog/frontend/package.json plugins/standard-catalog/frontend/package.json
COPY plugins/apis/frontend/package.json plugins/apis/frontend/package.json
COPY plugins/c4/frontend/package.json plugins/c4/frontend/package.json
COPY plugins/database-schema/frontend/package.json plugins/database-schema/frontend/package.json
COPY plugins/flows/frontend/package.json plugins/flows/frontend/package.json
COPY plugins/search/frontend/package.json plugins/search/frontend/package.json
RUN npm ci
COPY . .
RUN npm run build --workspace=frontend

FROM caddy:2-alpine AS caddy

FROM python:3.13.13-slim-bookworm
ENV DJANGO_ENV=production \
    DJANGO_SETTINGS_MODULE=server.settings \
    DJANGO_STATIC_ROOT=/var/www/django/static \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    PGDATA=/var/lib/atlas/pgdata \
    POSTGRES_DB=atlas \
    POSTGRES_USER=atlas \
    POSTGRES_PASSWORD=atlas \
    DJANGO_DATABASE_HOST=127.0.0.1 \
    DJANGO_DATABASE_PORT=5432

# uv's documented Docker install method: copy the static binary from its own
# published image, pinned to the version this repo's lock files were produced
# with — no network install step, no interpreter of its own to mismatch.
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /usr/local/bin/

RUN apt-get update && apt-get install --no-install-recommends -y \
      build-essential ca-certificates curl graphviz libpq-dev \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
      https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install --no-install-recommends -y postgresql-17 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin appuser

WORKDIR /code/core/backend
COPY core/backend/uv.lock core/backend/pyproject.toml ./
COPY composer /code/composer
COPY plugin-api/python /code/plugin-api/python
COPY plugins/auth-oidc/backend /code/plugins/auth-oidc/backend
COPY plugins/auth-gitea/backend /code/plugins/auth-gitea/backend
COPY plugins/standard-catalog/backend /code/plugins/standard-catalog/backend
COPY plugins/apis/backend /code/plugins/apis/backend
COPY plugins/c4/backend /code/plugins/c4/backend
COPY plugins/database-schema/backend /code/plugins/database-schema/backend
COPY plugins/ingestion/backend /code/plugins/ingestion/backend
COPY plugins/flows/backend /code/plugins/flows/backend
COPY plugins/search/backend /code/plugins/search/backend
COPY plugins/search-postgres/backend /code/plugins/search-postgres/backend
# Not selected in this demo distribution (see deploy/render/manifest.yaml), but
# core/backend/pyproject.toml/uv.lock list them as path dependencies, so
# `uv sync --frozen` needs its source present.
COPY plugins/mcp/backend /code/plugins/mcp/backend
COPY plugins/search-meilisearch/backend /code/plugins/search-meilisearch/backend
RUN uv sync --frozen --no-dev

COPY core/backend .
# Demo distribution (deploy/render/manifest.yaml): C4 diagrams are rendered by
# a remote PlantUML server instead of a local JVM, which would not fit in the
# free plan's 512 MB. Regenerate with deploy/render/compose.sh.
COPY deploy/render/selected_plugins.py server/settings/selected_plugins.py
# The official image gives caddy the cap_net_bind_service file capability. A
# non-root user without it in its bounding set gets "Operation not permitted"
# on exec, so copy the bytes only (no xattrs); we listen on $PORT >= 1024.
COPY --from=caddy /usr/bin/caddy /tmp/caddy-with-caps
RUN cat /tmp/caddy-with-caps > /usr/bin/caddy \
    && chmod 755 /usr/bin/caddy \
    && rm /tmp/caddy-with-caps
COPY --from=frontend /app/core/frontend/dist /srv/atlas
COPY deploy/render/Caddyfile /etc/caddy/Caddyfile
COPY deploy/render/start.sh /usr/local/bin/atlas-render-start
COPY deploy/render/build-demo-db.sh /usr/local/bin/atlas-build-demo-db
RUN chmod +x /usr/local/bin/atlas-render-start /usr/local/bin/atlas-build-demo-db \
    && mkdir -p "$DJANGO_STATIC_ROOT" /var/lib/atlas \
    && chown -R appuser:appuser /code "$DJANGO_STATIC_ROOT" /var/lib/atlas

USER appuser
ENV PATH="/usr/lib/postgresql/17/bin:${PATH}"
# Bake the demo into the image: initdb + migrate + seed + collectstatic.
RUN atlas-build-demo-db

EXPOSE 10000
CMD ["atlas-render-start"]
