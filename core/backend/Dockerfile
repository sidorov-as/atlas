# syntax=docker/dockerfile:1
FROM python:3.13.13-slim-bookworm AS base

ARG DJANGO_ENV=development
# UID/GID of the non-root `appuser` the `development`/`production` stages run as.
# Default 1000 matches the first regular user on most Linux hosts, so the
# development stage's bind-mounted source stays writable without an
# override; a host whose user has a different UID/GID can pass these build
# args to match it.
ARG APP_UID=1000
ARG APP_GID=1000
ENV DJANGO_ENV=${DJANGO_ENV} \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.4.1 \
    POETRY_HOME=/usr/local \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN apt-get update && apt-get install --no-install-recommends -y \
      build-essential curl default-jre-headless graphviz libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python - \
    && curl -fsSL -o /opt/plantuml.jar \
      https://github.com/plantuml/plantuml/releases/download/v1.2026.6/plantuml-1.2026.6.jar \
    && echo '89948f14c93756c7a3fb7b69078ff37e8489fd79dd430c582b931e2f65358690  /opt/plantuml.jar' | sha256sum -c - \
    && groupadd --gid "${APP_GID}" appuser \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home --shell /usr/sbin/nologin appuser
ENV PATH="/usr/local/bin:${PATH}"
ENV PLANTUML_BIN="" \
    PLANTUML_JAR=/opt/plantuml.jar

WORKDIR /code/core/backend
COPY core/backend/poetry.lock core/backend/pyproject.toml ./
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
RUN poetry install --no-root $(if [ "$DJANGO_ENV" = production ]; then echo --only main; fi)
# Keep the renderer self-contained: the C4 library is bundled by c4-diagrams
# and PlantUML runs locally, with no server URL or source mount dependency.
RUN dot -V \
    && printf '@startuml\nAlice -> Bob: local render\n@enduml\n' | java -jar "$PLANTUML_JAR" -tsvg -pipe > /tmp/plantuml-smoke.svg \
    && test -s /tmp/plantuml-smoke.svg \
    && rm /tmp/plantuml-smoke.svg

FROM base AS development
COPY core/backend .
RUN chmod +x docker/healthcheck.sh \
    && chown -R appuser:appuser /code
USER appuser
EXPOSE 8000
CMD ["python", "-We", "-bb", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS production
COPY core/backend .
ENV DJANGO_STATIC_ROOT=/var/www/django/static
RUN chmod +x docker/healthcheck.sh \
    && mkdir -p "$DJANGO_STATIC_ROOT" \
    && chown -R appuser:appuser /code "$DJANGO_STATIC_ROOT"
USER appuser
EXPOSE 8000
CMD ["gunicorn", "server.wsgi:application", "--bind", "0.0.0.0:8000"]
