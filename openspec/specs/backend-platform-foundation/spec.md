## Purpose

Provide Atlas with a reproducible, template-aligned Django backend foundation.

## Requirements

### Requirement: Template-aligned backend foundation
The backend SHALL be generated from and traceable to a pinned
`wemake-django-template` revision. It SHALL adopt that revision's application
layout, dependency workflow, settings architecture, Docker runtime, and
operational configuration, except for Sphinx documentation and GitLab CI.

#### Scenario: Auditable template provenance
- **WHEN** a maintainer inspects the backend migration documentation or configuration
- **THEN** they can identify the exact upstream template revision and excluded artifacts

#### Scenario: Atlas applications use the template foundation
- **WHEN** Django starts with the migrated backend
- **THEN** catalog and ingestion load from the template-aligned server layout with existing labels

### Requirement: Existing backend contracts remain compatible
The migration SHALL preserve Atlas REST routes, authentication integration,
data-model and migration identities, and frontend-facing behavior.

#### Scenario: Existing API routes remain available
- **WHEN** a client requests an admin, allauth, health, or catalog API route
- **THEN** its documented path and compatible behavior remain available

#### Scenario: Existing migrations remain valid
- **WHEN** Django evaluates migrations
- **THEN** catalog and ingestion history is recognized without unrelated model changes

### Requirement: Reproducible PostgreSQL-backed verification
The project SHALL document a local workflow that starts PostgreSQL and runs
the backend tests without an undocumented port override.

#### Scenario: Clean local test run
- **WHEN** a developer follows the documented workflow with Docker available
- **THEN** PostgreSQL is reachable and the full backend suite runs

#### Scenario: Compose and backend database settings agree
- **WHEN** Compose publishes PostgreSQL
- **THEN** backend defaults resolve the database without manual substitution

### Requirement: Baseline operational and security configuration
The backend SHALL include health reporting, structured logging, production
serving, security middleware, and explicit SPA session/CSRF configuration.
In a production environment (`DJANGO_ENV=production`), the backend SHALL
fail closed on unsafe or non-functional configuration rather than silently
falling back to development-safe defaults: it SHALL refuse to start with a
missing, placeholder, or insufficiently random `SECRET_KEY`, and it SHALL
NOT allow password-recovery to silently discard mail through a non-functional
mail backend.

#### Scenario: Health endpoint is available
- **WHEN** the backend service runs
- **THEN** its health endpoint reports success

#### Scenario: SPA session request remains valid
- **WHEN** the SPA sends an authenticated unsafe request from a configured origin
- **THEN** CSRF and origin validation accept the valid request

#### Scenario: Production startup rejects an unset or placeholder secret key
- **WHEN** the backend starts with `DJANGO_ENV=production` and `DJANGO_SECRET_KEY`
  is unset, equal to a known example/placeholder value, or shorter than the
  configured minimum length
- **THEN** startup fails with an error identifying the invalid setting, rather
  than falling back to a development secret

#### Scenario: Production startup accepts an explicit, sufficiently random secret key
- **WHEN** the backend starts with `DJANGO_ENV=production` and `DJANGO_SECRET_KEY`
  is explicitly set to a value that is not a known placeholder and meets the
  minimum length
- **THEN** startup proceeds normally

#### Scenario: Password recovery does not silently no-op in production
- **WHEN** the backend runs with `DJANGO_ENV=production` and no real mail
  backend is configured
- **THEN** password-recovery is not offered as a working feature (it is
  disabled or startup fails, rather than accepting requests and silently
  discarding the resulting email)

#### Scenario: Deployment checks pass with a correctly configured production environment
- **WHEN** `python manage.py check --deploy` runs with `DJANGO_ENV=production`,
  an explicit non-placeholder `SECRET_KEY`, and a real mail backend configured
- **THEN** it reports no errors related to secret key or mail configuration

### Requirement: Quality tooling is introduced without blocking remediation
The backend SHALL include template quality tooling, and Ruff findings across
every Python package (`core/backend`, `plugin-api/python`, and each
`plugins/*/backend`) SHALL be resolved against each package's own declared
Ruff configuration rather than left as open backlog.

#### Scenario: Functional migration is independently verifiable
- **WHEN** quality remediation is incomplete
- **THEN** Django and migration checks plus PostgreSQL-backed tests remain required

#### Scenario: Ruff reports zero findings
- **WHEN** `ruff check` runs against any Python package using that package's
  own `pyproject.toml` configuration
- **THEN** it reports zero violations, with no rule relaxed or excluded solely
  to suppress existing findings

#### Scenario: Quality debt from other tools remains visible
- **WHEN** a quality tool other than Ruff reports existing findings
- **THEN** those findings are recorded as bounded follow-up work, unaffected
  by this change

### Requirement: Reproducible full application runtime
The project SHALL provide documented Docker Compose workflows that build and
start the backend with its PostgreSQL dependency, ingestion worker, and
frontend in both source-mounted development and immutable production-like
modes.

#### Scenario: Production backend starts after schema initialization
- **WHEN** the production Compose workflow is started against an empty
  PostgreSQL volume
- **THEN** the backend begins serving only after migrations complete

#### Scenario: Development backend starts from mounted source
- **WHEN** a developer starts the documented development Compose workflow
- **THEN** the backend uses the mounted source directory and reaches its
  PostgreSQL service by the Compose hostname
