## Why

A developer currently has no single command to check, before pushing, that
their change will pass the fast checks CI runs on every PR: ruff, the
frontend test/build/lint suite, the backend pytest suite, and the migration
safety checks. Each is runnable individually today, but there's no
one-command local gate, and the migration safety check
(`django_safe_migrations.cli --diff origin/${{ base_ref }}`) additionally
depends on a freshly fetched `origin/main`, which a local run cannot
reliably guarantee the way CI's own checkout does.

The goal is a local `make ci` that gives real, fast confidence before a
push — not a local mirror of everything CI does. Heavy, matrix, or
network-dependent checks (the 5-topology `authentication-examples-integration`
Docker matrix, `npm audit`/`pip-audit`, `gitleaks`) stay CI-only: they're
either too slow for a pre-push loop, need external services/network, or
both, and CI already covers them on every PR.

## What Changes

- Add a `make ci` target that runs, locally and without Docker matrices:
  1. `make format-check` (existing) and `ruff check` across the same
     packages `ruff.yml` lints in CI (the `RUFF_PACKAGES` list already in
     the `Makefile` becomes the single source both the `Makefile` and
     `.github/workflows/ruff.yml` reference, removing the current
     duplication).
  2. Frontend: `npm ci`, `npm test -- --run`, `npm run build`,
     `npm run lint` (the same commands `frontend-checks.yml` runs, including
     its explicit sibling-package paths for `oxlint`).
  3. Backend: `pytest` against a throwaway, `make ci`-scoped PostgreSQL
     (see below), excluding tests marked `e2e` (see below).
  4. `check_migration_boundaries` (already dependency-free — no Docker, no
     git ref).
  5. `django_safe_migrations.cli --baseline <committed-baseline-file>`
     (see below) instead of CI's current `--diff origin/${{ base_ref }}`.
- Add `.ci/docker-compose.yml` with a single `postgres:17-alpine` service
  (`atlas`/`atlas`/`atlas`, matching CI) published on a dedicated port
  (`55432` by default) so it never collides with the `docker-compose.dev.yml`
  dev stack's `5432`. `DJANGO_DATABASE_PORT` is passed to `pytest`
  accordingly; no new settings module is needed since database settings
  already read from `POSTGRES_*`/`DJANGO_DATABASE_*` environment variables.
- Add a Make target (or `.ci/run.sh`) that starts that PostgreSQL with
  `--wait`, runs the steps above, always stops PostgreSQL afterward
  (`trap`), and prints a pass/fail summary per step.
- Generate and commit a migration-check baseline file
  (`core/backend/.migration-baseline.json`, via
  `check_migrations --generate-baseline`), capturing currently-known,
  already-shipped migration issues that don't have an inline
  `# safe-migrations: ignore ...` marker. `migration-lint.yml` in CI is
  updated to use `--baseline` instead of `--diff origin/${{ base_ref }}`,
  so the same command produces the same result locally and in CI — no
  `git fetch`, no dependency on `origin/main` freshness, in either
  environment.
- Register a `e2e` pytest marker (`pytest.ini` uses `--strict-markers`, so
  it must be declared) and apply it to
  `plugins/ingestion/backend/atlas_plugin_ingestion/tests/test_git_connector_integration.py`
  (the only test module in the backend suite that spins up a real Docker
  container). `make ci`'s pytest step runs with `-m "not e2e"`, so it never
  needs Docker-in-Docker or a mounted `docker.sock`, and it never silently
  skips a test that a developer would expect to see marked, pass, or fail.
  CI's `backend-tests` job is unaffected: it continues to run the full,
  unfiltered suite, including the `e2e`-marked test, exactly as it does
  today. Rewriting that test's container setup (e.g. `testcontainers`) and
  giving it its own dedicated CI job is tracked as separate, future work —
  this change only adds the marker needed for `make ci` to exclude it
  deterministically.
- Document, in the root README or a `.ci/README.md`, that Python version
  and dependency setup for `core/backend` (and therefore for the backend
  pytest step) is handled by `uv` — this change assumes `migrate-backend-to-uv`
  has already landed; see Impact.

Explicitly out of scope for `make ci` (stays CI-only, no local target added):
`authentication-examples-integration`'s 5-topology Docker matrix,
`dependency-audit` (`npm audit`, `pip-audit`), `secret-scan` (`gitleaks`).

## Capabilities

### New Capabilities

- `local-ci-workflow`: a one-command local workflow (`make ci`) that runs
  linting and the fast/non-matrix backend and frontend test suites against
  a throwaway, isolated PostgreSQL instance, giving a developer push-ready
  confidence without needing the heavy/matrix CI checks locally.

### Modified Capabilities

- `expand-contract-migrations`: the "Destructive migrations are blocked
  outside maintenance mode" requirement currently doesn't specify how the
  check scopes itself to "this change's" migrations. This change makes that
  scoping mechanism an explicit, committed baseline file instead of a
  git-ref diff, so the same check produces the same result locally and in
  CI without depending on a freshly fetched base branch.

## Impact

- **Code**: root `Makefile` (new `ci` target and helpers), new
  `.ci/docker-compose.yml`, new `.ci/run.sh` (or equivalent Make plumbing),
  new `core/backend/.migration-baseline.json`, `pytest.ini` (register the
  `e2e` marker), the SSH-clone test module (add the marker).
- **CI**: `migration-lint.yml` switches from `--diff origin/${{ base_ref }}`
  to `--baseline`; `ruff.yml` and the `Makefile` share one package list.
  `backend-tests.yml`, `frontend-checks.yml` are otherwise unchanged — they
  keep running the full, unfiltered suites they run today.
- **Dependency**: assumes the backend workspace already runs on `uv`
  (tracked separately as the `migrate-backend-to-uv` change) so `make ci`'s
  backend steps have one dependency workflow to install against, not a
  choice between two.
- **Out of scope**: no change to `authentication-examples-integration.yml`,
  `dependency-audit.yml`, or `secret-scan.yml` — they remain CI-only.
- **Developer workflow**: a developer can run `make ci` locally before
  pushing and get the same lint/test/migration verdicts CI's fast checks
  would give, without Docker matrices or network access (beyond `npm ci`).
