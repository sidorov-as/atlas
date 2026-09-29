## Context

The repository has a source-mounted root Compose file for development and a
separate backend-only production draft. The latter lacks PostgreSQL and the
frontend, declares an unmet health dependency, and does not share Django's
collected static assets with Caddy. The frontend Dockerfile only starts Vite's
development server.

Atlas is a Django application, a long-running ingestion worker, PostgreSQL,
and a Vite SPA. Development requires rapid source reloads; production requires
immutable built artifacts and one same-origin public entrypoint.

## Goals / Non-Goals

**Goals:**

- Provide distinct, unambiguous Compose entrypoints for development and
  production-like operation.
- Make each service rebuild only when its dependencies or production source
  artifact changes, while source changes reload without rebuild in dev.
- Expose the SPA and Django routes through one production origin.
- Make migrations and static collection explicit, ordered, and repeatable.
- Document supported launch and operational workflows from the repository root.

**Non-Goals:**

- Deploy Atlas to a cloud platform, provision TLS certificates, or introduce an
  external image registry.
- Replace Django sessions, authentication, database technology, or the
  ingestion architecture.
- Provide hot-reload semantics in the production topology.

## Decisions

### Use separate production and development Compose files

`docker-compose.yml` SHALL be the production-like topology and
`docker-compose.dev.yml` SHALL be the source-mounted development topology.
This makes `docker compose up --build` safe as the default production artifact
check while keeping local iteration an explicit command.

An override-file design (`docker compose -f docker-compose.yml -f
docker-compose.dev.yml`) was considered. Two independently runnable files are
clearer here because service commands, mounts, and public routing differ
materially rather than merely adding a few local overrides.

### Build frontend artifacts and serve them from the production gateway

The frontend Dockerfile SHALL use stages: an install stage keyed by lockfiles,
a Vite build stage, and a small production static-server stage. The latter is
the public gateway: it serves SPA assets and history fallback, proxies Django
routes (`/api`, `/_allauth`, `/admin`), and serves Django static assets from a
shared named volume.

This is preferred to exposing a separate backend port or retaining Vite in
production. Relative browser requests already match the Vite development proxy,
so a same-origin gateway avoids a second CORS/public-origin configuration.

### Separate immutable service images from mutable runtime data

Production uses built backend and frontend images without source mounts.
PostgreSQL data and Django static assets use named volumes. A one-shot
initialization service using the backend production image runs migrations and
collects static assets into the static volume before the backend, ingestor, and
gateway are considered ready to run. The Compose dependency graph uses database
health and successful initializer completion rather than timing delays.

Automatic migrations in every web container entrypoint were rejected because
they race when replicas are later introduced and hide a schema-changing
operation inside a long-running process.

### Retain development bind mounts with protected dependency paths

The dev topology mounts `./backend` and `./frontend` into their respective
working directories, runs Django's development server and Vite HMR, and keeps
installed JavaScript dependencies in a container-managed volume. It retains
PostgreSQL data in a named volume and exposes the documented local ports.
Backend dependency installation stays in the image layer; developers rebuild
only after changing Poetry dependency metadata.

### Make operational documentation a root-level source of truth

The root README SHALL own prerequisites, environment setup, the exact dev and
production commands, URLs, migrations, logs, stopping, and data reset. Backend
and frontend README files SHALL retain component-specific commands only and
link to the root guide, preventing conflicting instructions.

## Risks / Trade-offs

- [Named static volume is empty on first run] → the initializer must complete
  static collection before the gateway begins serving static files.
- [Migrations fail due to credentials or incompatible schema] → the initializer
  exits non-zero and prevents dependent services from starting; logs identify
  the failed command.
- [Frontend routes are refreshed directly] → configure SPA fallback after
  static-file lookup while keeping Django route prefixes proxied.
- [Host file ownership or filesystem events differ by OS] → use named volumes
  for dependency directories and document the supported Docker Desktop flow.
- [Production needs TLS] → scope this topology to a production-like HTTP
  deployment; let an external ingress or future change own certificate policy.

## Migration Plan

1. Introduce production and dev Compose files, staged images, gateway config,
   and explicit initialization service.
2. Validate both rendered Compose configurations and build/start each topology.
3. Replace duplicate launch instructions with the root guide.
4. Existing users of the current root development command migrate to the new
   documented `-f docker-compose.dev.yml` command; no application data migration
   is required because the named PostgreSQL volume remains the data store.
5. Roll back by restoring the former Compose entrypoint; Docker volumes are not
   removed by the change and remain recoverable.

## Open Questions

- Production secret and domain values will remain operator-supplied through an
  env file; selecting a secrets manager is outside this change.
- CI image publication and deployment automation are deliberately deferred.
