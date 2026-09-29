## ADDED Requirements

### Requirement: Template-aligned backend foundation
The backend SHALL be generated from and traceable to a pinned
`wemake-django-template` revision. It SHALL adopt that revision's application
layout, dependency workflow, settings architecture, Docker runtime, and
operational configuration, except for Sphinx documentation and GitLab CI.

#### Scenario: Auditable template provenance
- **WHEN** a maintainer inspects the backend migration documentation or
  configuration
- **THEN** they can identify the exact upstream template revision used and the
  intentionally excluded Sphinx and GitLab CI artifacts

#### Scenario: Atlas applications use the template foundation
- **WHEN** Django starts with the migrated backend
- **THEN** the catalog and ingestion applications load from the template-aligned
  server layout while retaining their existing Django app labels

### Requirement: Existing backend contracts remain compatible
The migration SHALL preserve existing Atlas REST routes, authentication
integration, data-model and migration identities, and frontend-facing backend
behavior unless a separately approved specification changes those contracts.

#### Scenario: Existing API routes remain available
- **WHEN** a client requests the existing admin, allauth, health, or catalog
  API route after the migration
- **THEN** the route retains its documented path and compatible response or
  authentication behavior

#### Scenario: Existing migrations remain valid
- **WHEN** Django evaluates the migrated project's migrations
- **THEN** it recognizes the existing catalog and ingestion migration history
  without proposing unrelated model changes

### Requirement: Reproducible PostgreSQL-backed verification
The project SHALL provide a documented local command or workflow that starts a
compatible PostgreSQL dependency and runs the backend test suite without an
undocumented database-port override.

#### Scenario: Clean local test run
- **WHEN** a developer follows the documented backend test workflow from a
  clean checkout with Docker available
- **THEN** PostgreSQL is reachable using the configured environment contract
  and the full backend pytest suite runs against it

#### Scenario: Compose and backend database settings agree
- **WHEN** Docker Compose publishes the local PostgreSQL service
- **THEN** the backend default database host and port resolve to that service
  without manual environment substitution

### Requirement: Baseline operational and security configuration
The migrated backend SHALL include template-provided health reporting,
structured logging, production serving configuration, and applicable security
middleware/settings, with Atlas SPA session and CSRF behavior configured
explicitly.

#### Scenario: Health endpoint is available
- **WHEN** the backend service is running
- **THEN** its configured health endpoint reports a successful health status

#### Scenario: SPA session request remains valid
- **WHEN** the Atlas SPA sends an authenticated unsafe request from an
  explicitly configured development or production origin
- **THEN** the backend applies CSRF and origin validation without rejecting the
  valid request solely because of the template security defaults

### Requirement: Quality tooling is introduced without blocking remediation
The backend SHALL contain the quality-tool dependencies and configuration from
the pinned template, but full legacy-source compliance SHALL be tracked as
separate follow-up work rather than blocking this platform migration.

#### Scenario: Functional migration is independently verifiable
- **WHEN** the template migration is evaluated before quality remediation is
  complete
- **THEN** Django checks, migration checks, and the full PostgreSQL-backed test
  suite are required to pass independently of unresolved strict lint or typing
  findings

#### Scenario: Quality debt is visible
- **WHEN** configured quality tools report findings in existing Atlas source
- **THEN** the findings are recorded in bounded follow-up tasks or changes
  rather than silently discarded or mixed into unrelated functional changes
