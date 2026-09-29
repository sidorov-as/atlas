## MODIFIED Requirements

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
