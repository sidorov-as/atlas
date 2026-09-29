## 1. Container image foundations

- [x] 1.1 Refactor the backend Dockerfile into verified development and production targets, including a production static-output location usable by the gateway.
- [x] 1.2 Refactor the frontend Dockerfile into dependency, Vite-build, development, and production gateway targets.
- [x] 1.3 Add production gateway configuration for static SPA files, history fallback, Django route proxying, and shared Django static files.
- [x] 1.4 Update Docker ignore files and environment examples for the revised build contexts and production configuration.

## 2. Compose topologies

- [x] 2.1 Replace the root `docker-compose.yml` with the production-like topology containing PostgreSQL, initializer, backend, ingestor, and public frontend gateway.
- [x] 2.2 Configure named data/static volumes, internal networks, health checks, and dependency conditions so startup follows database health and initializer success.
- [x] 2.3 Create `docker-compose.dev.yml` with source mounts, Django autoreload, Vite HMR, protected dependency volumes, PostgreSQL, and ingestor.
- [x] 2.4 Retire or redirect the obsolete backend-only production Compose definition so there is no competing production entrypoint.

## 3. Documentation

- [x] 3.1 Write the root README as the authoritative guide for prerequisites, environment setup, dev and production commands, URLs, and health verification.
- [x] 3.2 Document migrations, logs, stopping services, and intentionally resetting Compose data in the root README.
- [x] 3.3 Update backend and frontend README files with component-specific host workflows and links to the root full-stack guide.

## 4. Verification

- [x] 4.1 Validate both Compose files with `docker compose config` using documented environment inputs.
- [x] 4.2 Build and start the development topology; verify backend health, frontend-to-backend proxying, source reload behavior, and ingestor startup.
- [x] 4.3 Build and start the production-like topology from a clean state; verify migration/static initialization, SPA route fallback, API proxying, and absence of backend source mounts.
- [x] 4.4 Run the relevant backend and frontend test/lint suites and record any environment-specific manual verification in the change artifacts.

## Verification record

- `docker compose --env-file backend/.env config --quiet` and its
  `docker-compose.dev.yml` counterpart both completed successfully.
- Development topology built and started successfully. PostgreSQL and backend
  became healthy; Vite served the frontend; Django migration completed; and the
  ingestor started after migrations. Source directories and the protected
  frontend `node_modules` volume were present in the rendered topology.
- Production-like topology was started against its fresh `postgres-data` and
  `django-static` volumes. The initializer completed migrations and collected
  148 static files before backend, ingestor, and Caddy started. Gateway health
  proxying and SPA fallback were verified on `http://localhost:8080`; backend
  had no mounts.
- Backend suite: `91 passed` (`pytest`). Frontend `npm run lint` exited 0 with
  10 existing warnings. Frontend `npm test` had 16 passing and 1 failing test:
  `src/lib/flowLayout.test.ts` expects layout options without the existing
  `elk.layered.spacing.nodeNodeBetweenLayers` value. This failure is unrelated
  to the container/runtime changes and was not modified in this change.
