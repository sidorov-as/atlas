## Why

Atlas does not currently provide a complete, documented path for either local
development or a production-like deployment. The root Compose file is a dev
configuration despite its generic name, while the backend-only production
Compose file cannot start the full topology or serve its static assets
correctly.

## What Changes

- Define a production `docker-compose.yml` that builds and starts PostgreSQL,
  backend, ingestor, and the compiled frontend behind one public gateway.
- Add a `docker-compose.dev.yml` for local development that bind-mounts backend
  and frontend sources while preserving container-managed dependencies.
- Make backend and frontend Dockerfiles support the distinct development and
  production runtime requirements.
- Define reliable startup behavior for database readiness, migrations, Django
  static assets, health checks, and service dependencies.
- Consolidate backend, frontend, and full-stack launch instructions into a
  single authoritative root README, with focused component README links.

## Capabilities

### New Capabilities

- `containerized-runtime`: Reproducible dev and production Compose topologies
  for the complete Atlas application.
- `developer-launch-documentation`: Authoritative instructions for starting,
  configuring, verifying, and resetting Atlas locally and in production-like
  containers.

### Modified Capabilities

- `backend-platform-foundation`: Extend the platform's reproducibility contract
  from database test setup to complete application startup and delivery.

## Impact

- Affected files: root Compose files, both service Dockerfiles, Caddy/static
  serving configuration, environment examples, and README files.
- Affected runtime systems: Docker Compose, PostgreSQL, Django/Gunicorn,
  ingestion worker, Vite development server, and production static frontend.
- No public API contract changes are intended.
