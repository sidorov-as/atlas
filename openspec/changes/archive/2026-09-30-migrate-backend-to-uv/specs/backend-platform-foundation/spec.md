## MODIFIED Requirements

### Requirement: Template-aligned backend foundation
The backend SHALL be generated from and traceable to a pinned
`wemake-django-template` revision. It SHALL adopt that revision's
application layout, settings architecture, Docker runtime, and operational
configuration, except for Sphinx documentation, GitLab CI, and the
dependency workflow. The dependency workflow SHALL use `uv` (a single
`uv.lock` per shared workspace root) instead of the template's inherited
Poetry-based workflow; this is a deliberate, documented departure from the
template, not an omission.

#### Scenario: Auditable template provenance
- **WHEN** a maintainer inspects the backend migration documentation or
  configuration
- **THEN** they can identify the exact upstream template revision, the
  excluded artifacts, and the documented dependency-workflow departure

#### Scenario: Atlas applications use the template foundation
- **WHEN** Django starts with the migrated backend
- **THEN** catalog and ingestion load from the template-aligned server
  layout with existing labels

#### Scenario: Dependency workflow uses uv, not the inherited Poetry setup
- **WHEN** a maintainer inspects `core/backend`, `plugin-api/python`, or any
  `plugins/*/backend` package's dependency configuration
- **THEN** it resolves and installs through `uv` (`pyproject.toml` plus a
  `uv.lock`), with no `poetry.lock`, `poetry.toml`, or
  `poetry-core` build-system declaration present
