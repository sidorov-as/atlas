## Why

The backend was originally intended to be scaffolded from
`wemake-django-template`, but the delivered project is a minimal Django
configuration rather than an adoption of that template. It lacks the
template's operational structure, security defaults, and reproducible
development/test workflow; moreover, its configured PostgreSQL port does not
match Docker Compose, so the test suite requires a manual override to run.

## What Changes

- Adopt a pinned revision of `wemake-django-template` as the backend
  foundation, excluding Sphinx documentation and GitLab CI configuration.
- Migrate the Atlas backend's packaging, settings layout, environment
  configuration, Docker development/production runtime, health checks,
  structured logging, and security middleware to the template conventions.
- Upgrade Django only as required by the selected template revision, preserving
  the existing Atlas API, data model, migrations, and externally visible
  behavior.
- Establish a repeatable PostgreSQL-backed test workflow that passes without
  per-developer port overrides.
- Introduce the template's quality-tool configuration and dependencies without
  making full linter/type-check remediation a prerequisite of this change.

## Capabilities

### New Capabilities

- `backend-platform-foundation`: A template-aligned backend runtime with
  reproducible local/test execution, health reporting, and baseline security
  configuration.

### Modified Capabilities

None.

## Impact

- Affects `backend/`, root Docker Compose configuration, backend environment
  examples, dependency/lock files, and developer commands.
- Replaces the current minimal settings and container setup with a
  template-aligned layout while retaining the `catalog` and `ingestion`
  applications and their migrations.
- Changes the Python dependency manager to the one used by the pinned template
  revision and may update Django and related packages.
- Does not add Sphinx artifacts or GitLab CI, and does not intentionally change
  frontend behavior or Atlas API contracts.
