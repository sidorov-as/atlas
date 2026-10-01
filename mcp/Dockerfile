# syntax=docker/dockerfile:1
#
# A local build only (`docker build -t atlas-mcp .`) — this repository does
# not publish or version this image (design.md's Non-Goals: "Publishing a
# versioned MCP transport image to a public registry ... is left to whoever
# runs that Atlas instance").
FROM python:3.13.13-slim-bookworm

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/usr/local

# Same pinned uv binary core/backend's own Dockerfile uses — no network
# install step, no interpreter of its own to mismatch.
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /usr/local/bin/

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin appuser

WORKDIR /code/mcp
COPY pyproject.toml uv.lock README.md ./
COPY atlas_mcp ./atlas_mcp
RUN uv sync --frozen --no-dev \
    && chown -R appuser:appuser /code

USER appuser

# stdio only: the MCP client that launches this container owns its
# stdin/stdout entirely (see README.md's client config) — nothing here
# listens on a port, so no `EXPOSE`.
ENTRYPOINT ["atlas-mcp"]
