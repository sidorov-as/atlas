## Context

`bootstrap-catalog-service` specified `wemake-django-template`, but the
current `backend/` is a hand-built, minimal Django 5.2 project using uv, a
`config.settings.{base,local,production}` package, and one-stage Dockerfile.
It has no template-compatible operational layout or quality-tool baseline.
The full PostgreSQL test suite is healthy (89 tests) when pointed at a running
database on port 5432, but the checked-in Compose default and local backend
environment use different host ports.

The selected upstream template revision must be pinned before implementation:
the repository is actively maintained and its supported Django version changes
over time. The migration must preserve the Atlas REST API, database schema,
and existing catalog/ingestion behavior. Sphinx and GitLab CI are explicitly
out of scope.

## Goals / Non-Goals

**Goals:**

- Make the generated structure and runtime conventions of a pinned
  `wemake-django-template` revision the backend foundation.
- Preserve all existing Django app labels, migrations, API paths, and frontend
  integration while adapting application imports and configuration to that
  foundation.
- Adopt the template's dependency manager, Docker multi-stage runtime,
  environment contract, settings components, health checks, structured
  logging, and security-related Django integrations.
- Make the documented test command provision or target a compatible local
  PostgreSQL instance without hidden port overrides, and prove the existing
  suite passes after migration.
- Add the template quality-tool configuration and dependencies while deferring
  source-wide lint and typing remediation to follow-up changes.

**Non-Goals:**

- Adding Sphinx documentation, GitLab CI, or a replacement CI provider.
- Altering Atlas API resources, authorization policy, database data model, or
  frontend product behavior.
- Rewriting the catalog or ingestion applications merely to satisfy linter or
  type-check findings.
- Treating an automatic Django upgrade as sufficient validation; test and
  migration compatibility remain mandatory.

## Decisions

### Pin and generate from an upstream template revision

Implementation SHALL record the upstream commit SHA and generate a fresh
template project from that revision in a disposable workspace. Atlas-specific
modules and configuration SHALL then be ported into that generated structure,
rather than copying an unpinned set of files from the default branch.

This makes the resulting baseline auditable and reproducible. Directly
incrementally editing the current skeleton would retain unknown drift from the
template; replacing the whole backend without porting applications would risk
losing migrations and behavior.

### Use the template's server package and preserve Django identities

Atlas application modules SHALL move into the template's canonical server
layout, with import paths and Django settings updated consistently. Their
Django app labels (`catalog`, `ingestion`) and migration history SHALL remain
stable, so existing tables and migration dependencies continue to resolve.
Public URLs (`/api`, `/_allauth`, `/admin`, `/healthz`) SHALL remain unchanged.

Retaining the current `config` layout was rejected because it would make the
result a partial adoption. Changing app labels was rejected because it risks
database table and migration identity changes unrelated to this infrastructure
migration.

### Adopt template runtime/security components behind compatibility tests

The generated dependency and settings baseline SHALL include the template's
runtime and security components (including split settings, environment parsing,
structured logging, health checks, CORS/CSRF support, CSP, permissions policy,
rate/abuse protection where compatible, and production WSGI/ASGI serving).
Atlas-specific allauth, PostgreSQL, ingestion, and SPA proxy configuration
SHALL be merged into that baseline.

Components whose defaults change observable API behavior SHALL be configured
explicitly and covered by existing or targeted compatibility tests. Removing
them to avoid configuration work was rejected because it defeats adopting the
template's operational foundation.

### Migrate packaging and containers as one reproducible unit

The backend SHALL use the package manager and lock-file workflow supplied by
the pinned template. Docker build targets and compose services SHALL be based
on the template's development and production topology, then extended for the
existing frontend and `ingestor` process. The template's Caddy/production
artifacts are included; Sphinx and `.gitlab-ci.yml` are not.

Keeping uv beside the template's package workflow was rejected because two
lock-file authorities would make builds non-reproducible. Keeping the existing
single-stage Dockerfile was rejected because it omits the template runtime
contract.

### Treat Django upgrade as an explicit compatibility migration

The target Django version SHALL be the version range of the pinned template.
Before changing Atlas source, implementation SHALL inventory Django
deprecations and run `django-codemod` in reviewable passes where it supports
the target version. Its edits SHALL be reviewed and followed by Django checks,
migration checks, and the full test suite; unsupported deprecations are manual
work items.

`django-codemod` is a CLI for automated deprecation rewrites, not a runtime
dependency or a substitute for tests. Skipping codemods entirely would make
the upgrade more manual; installing it into production dependencies would add
unnecessary runtime surface.

### Stage quality enforcement after runtime compatibility

Ruff/wemake, mypy/django-stubs, migration safety, coverage, and test quality
tools SHALL be present and documented, but this change SHALL not require the
legacy Atlas source to pass their full strict profile. Each failing category
SHALL be captured as a follow-up task/change with a bounded scope. The core
gate for this change is a functional, PostgreSQL-backed test suite plus Django
system and migration checks.

Enabling every quality gate as blocking in this migration was rejected because
it would blur platform adoption with broad refactoring and delay a working
baseline.

## Risks / Trade-offs

- [Risk] Template's supported Django version may introduce API removals or
  third-party compatibility changes → Mitigation: pin first, inventory
  deprecations, run codemods selectively, and require checks plus the complete
  test suite after each compatibility milestone.
- [Risk] Moving Python package paths can break imports, management commands,
  migrations, or deployed entry points → Mitigation: preserve Django app
  labels, update imports mechanically, and validate `showmigrations`,
  `makemigrations --check`, and management commands.
- [Risk] Security middleware can reject the SPA's current session/CSRF traffic
  → Mitigation: preserve explicit Vite/Caddy origins and add request-level
  regression coverage before enforcing production defaults.
- [Risk] Docker topology changes can make frontend or ingestor unable to reach
  the backend/database → Mitigation: keep the service contract in Compose and
  test development startup plus health endpoints.
- [Risk] Tooling discovery creates a large remediation backlog → Mitigation:
  collect tool output as an inventory and create separate prioritized changes;
  do not weaken functional verification.

## Migration Plan

1. Capture a clean functional baseline: start the documented PostgreSQL
   service, run the 89-test suite, and record current API/migration checks.
2. Pin and generate the upstream template, then port Atlas applications,
   migrations, environment variables, containers, and service commands into
   its structure.
3. Upgrade Django and dependencies to the pin's supported versions; apply
   reviewed codemods and manual compatibility changes.
4. Align Compose and backend environment defaults, run migrations/checks, and
   verify backend, ingestor, and frontend integration points.
5. Run the complete PostgreSQL-backed suite and record quality-tool findings as
   follow-up work.

Rollback is a normal source/dependency rollback to the pre-migration revision;
no intentional schema migration or data transformation is part of this change.

## Open Questions

- Which exact upstream commit and corresponding Django major version should be
  pinned after compatibility reconnaissance?
- Does production deployment require the template's Caddy topology immediately,
  or only its committed production artifacts while current deployment behavior
  remains unchanged?
- Which initial quality checks can be enabled as non-blocking reports without
  destabilizing contributors' local workflows?
