## ADDED Requirements

### Requirement: Full-project checks are required before merge
CI SHALL run and require, for every pull request targeting the default
branch: the full backend pytest suite across `core/backend` and every
plugin backend, frontend test/build/lint, `ruff check` for every Python
package against that package's own configuration, `npm audit
--audit-level=high`, `pip-audit`, and a secret scan of the PR's changes.

#### Scenario: Backend test failure blocks merge
- **WHEN** a pull request introduces a failing backend test in any plugin
  backend
- **THEN** the required backend-tests check fails and the pull request
  cannot merge

#### Scenario: Frontend build or lint failure blocks merge
- **WHEN** a pull request breaks the frontend build or introduces a lint
  violation
- **THEN** the required frontend check fails and the pull request cannot
  merge

#### Scenario: Ruff violation blocks merge
- **WHEN** a pull request introduces a new Ruff violation in any Python
  package
- **THEN** the required Ruff check fails and the pull request cannot merge

#### Scenario: High-severity dependency vulnerability blocks merge
- **WHEN** a pull request's dependency changes introduce a new high-severity
  `npm audit` or `pip-audit` finding
- **THEN** the required dependency-audit check fails and the pull request
  cannot merge

#### Scenario: Detected secret blocks merge
- **WHEN** a pull request's diff contains content the secret scanner flags
- **THEN** the required secret-scan check fails and the pull request cannot
  merge

### Requirement: CI action references are pinned to commit SHA
Every third-party GitHub Action referenced in `.github/workflows/` or
`.github/actions/` SHALL be pinned to a full commit SHA rather than a
mutable tag or branch reference, and an automated dependency-update tool
SHALL be configured to propose pin updates.

#### Scenario: Action reference uses a commit SHA
- **WHEN** a workflow or composite action references a third-party GitHub
  Action
- **THEN** the reference is a full commit SHA, not a tag such as `@v4`

#### Scenario: Automated updates are proposed for pinned actions
- **WHEN** a pinned action publishes a new release
- **THEN** the repository's dependency-update configuration opens a pull
  request updating the pin to the new commit SHA
