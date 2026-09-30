# local-ci-workflow Specification

## Purpose
A one-command local workflow (`make ci`) that mirrors CI's fast checks —
linting, frontend and backend tests, migration safety checks — against a
throwaway PostgreSQL, giving a developer push-ready confidence before a push
without needing Docker matrices or network access.

## Requirements

### Requirement: One-command local lint and test verification
The project SHALL provide a `make ci` target that runs, in a single command,
the same linting and non-matrix test checks CI's fast checks run: backend
Ruff linting, the frontend test/build/lint suite, the backend pytest suite
(excluding tests marked `e2e`), `check_migration_boundaries`, and the
migration destructive-operation check.

#### Scenario: Clean push-ready run
- **WHEN** a developer with Docker available runs `make ci` on a change
  that would pass CI's fast checks
- **THEN** `make ci` exits successfully, having run ruff, the frontend
  suite, the backend pytest suite, and the migration checks

#### Scenario: A failing step is identified
- **WHEN** any individual step (ruff, frontend, backend pytest, or a
  migration check) fails
- **THEN** `make ci` reports which step failed and exits non-zero, without
  requiring the developer to re-run steps individually to find out

#### Scenario: Heavy/matrix checks are not run locally
- **WHEN** a developer runs `make ci`
- **THEN** it does not run the `authentication-examples-integration`
  Docker-topology matrix, `npm audit`/`pip-audit`, or `gitleaks` — these
  remain CI-only

### Requirement: Isolated, throwaway PostgreSQL for local backend tests
`make ci`'s backend pytest step SHALL run against a PostgreSQL instance
that is started and stopped for that run alone, on a port dedicated to
`make ci` and distinct from the development stack's PostgreSQL port, so
`make ci` never collides with or mutates a developer's running dev stack.

#### Scenario: make ci runs alongside a running dev stack
- **WHEN** a developer has `make dev-up`'s PostgreSQL already running and
  then runs `make ci`
- **THEN** `make ci` starts its own PostgreSQL on a different port and
  neither instance's data is affected by the other

#### Scenario: PostgreSQL is always stopped after the run
- **WHEN** `make ci` finishes, whether its checks passed or failed
- **THEN** the PostgreSQL instance it started is stopped

### Requirement: Docker-dependent tests are excluded from the local run, not silently skipped
Tests that require Docker to run themselves (as opposed to `make ci`'s own
PostgreSQL, which the developer's environment already needs) SHALL be
marked with an explicit, registered `pytest` marker and excluded from
`make ci`'s pytest invocation by that marker, rather than left to an
environment-dependent self-skip.

#### Scenario: Docker-dependent test is excluded deterministically
- **WHEN** `make ci` runs its backend pytest step
- **THEN** any test marked `e2e` is deselected regardless of whether Docker
  is reachable from the process running `make ci`

#### Scenario: CI's full suite still covers the excluded test
- **WHEN** CI's `backend-tests` workflow runs
- **THEN** it runs the full, unfiltered suite, including tests marked `e2e`
