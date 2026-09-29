## 1. Baseline and upstream selection

- [x] 1.1 Record the current backend API, migration, and PostgreSQL-backed test baseline, including the configured database-port mismatch.
- [x] 1.2 Select and record an exact `wemake-django-template` commit SHA, its Python/Django compatibility range, and the template artifacts in scope.
- [x] 1.3 Generate the selected template in a disposable workspace and compare its application layout, dependencies, settings, Docker files, and environment contract with Atlas.
- [x] 1.4 Explicitly exclude Sphinx and GitLab CI artifacts from the adoption inventory.

## 2. Template foundation and application port

- [x] 2.1 Replace the backend packaging metadata and lock-file workflow with the selected template's dependency workflow, adding Atlas runtime dependencies and retaining no competing lock-file authority.
- [x] 2.2 Add the template server-package, split-settings, environment, logging, health-check, and production entry-point structure.
- [x] 2.3 Port the catalog and ingestion modules, tests, management commands, URLs, and ASGI/WSGI configuration into the template layout.
- [x] 2.4 Preserve `catalog` and `ingestion` Django app labels and verify existing migrations remain recognized without unrelated generated migrations.
- [x] 2.5 Merge Atlas allauth, PostgreSQL, ingestion, and SPA CSRF/origin settings into the template configuration while preserving `/api`, `/_allauth`, `/admin`, and `/healthz` contracts.

## 3. Django and dependency compatibility

- [x] 3.1 Upgrade Django and third-party packages to the selected template-compatible versions and regenerate the lock file.
- [x] 3.2 Inventory deprecations, run supported `django-codemod` transformations in reviewable passes, and make required manual compatibility fixes.
- [x] 3.3 Run Django system checks, `showmigrations`, and `makemigrations --check`; resolve only migration or runtime compatibility failures.
- [x] 3.4 Add or adapt regression tests for any template security defaults that affect session, CSRF, CORS, CSP, or API behavior.

## 4. Container and developer workflow

- [x] 4.1 Replace the backend Dockerfile and development Compose topology with the selected template's multi-stage/container conventions.
- [x] 4.2 Integrate the existing frontend and ingestor services into the template Compose network, dependency, volume, and health-check topology.
- [x] 4.3 Add the template production artifacts, including Caddy where supplied by the selected revision, without adding Sphinx or GitLab CI.
- [x] 4.4 Align Compose and backend environment defaults so the documented PostgreSQL test workflow requires no manual port override.
- [x] 4.5 Document the canonical development, migration, health-check, and PostgreSQL-backed test commands.

## 5. Verification and quality follow-up

- [x] 5.1 Verify a clean template-based backend startup, health endpoint, migrations, catalog API, allauth flow, and ingestor command.
- [x] 5.2 Run the full PostgreSQL-backed backend pytest suite and resolve all functional regressions.
- [x] 5.3 Add the selected template's lint, formatting, typing, migration-safety, coverage, and test-quality tool configuration without making unresolved legacy findings blocking.
- [x] 5.4 Run the configured quality tools, capture their findings, and create bounded follow-up OpenSpec changes or tasks for remediation.
