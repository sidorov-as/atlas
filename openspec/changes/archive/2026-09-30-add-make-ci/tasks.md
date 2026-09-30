## 1. Prerequisite

- [x] 1.1 Confirm `migrate-backend-to-uv` has landed (backend pytest step
      below assumes one working `uv`-based install path for
      `core/backend` + plugin backends)

## 2. Docker-dependent test carve-out

- [x] 2.1 Register the `e2e` marker in `pytest.ini` (required by
      `--strict-markers`)
- [x] 2.2 Apply `@pytest.mark.e2e` (or module-level `pytestmark`) to
      `plugins/ingestion/backend/atlas_plugin_ingestion/tests/test_git_connector_integration.py`
- [x] 2.3 Confirm `backend-tests.yml` (full, unfiltered `pytest`) still
      runs and passes that test in CI, unaffected

## 3. Migration baseline

- [x] 3.1 Generate `core/backend/.migration-baseline.json` via
      `check_migrations --generate-baseline`, review its contents
- [x] 3.2 Commit the baseline file
- [x] 3.3 Update `migration-lint.yml` to run
      `django_safe_migrations.cli --baseline core/backend/.migration-baseline.json`
      (dropping `--diff origin/${{ base_ref }}` and the `git fetch` step)
- [x] 3.4 Confirm CI's migration-lint job still fails on a deliberately
      introduced destructive migration (manual smoke test) and passes
      otherwise

## 4. `.ci/` scaffolding

- [x] 4.1 Add `.ci/docker-compose.yml`: one `postgres:17-alpine` service
      (`atlas`/`atlas`/`atlas`), published on port `55432` by default
- [x] 4.2 Add a Make target/`.ci/run.sh` that starts it with `--wait`,
      exports `DJANGO_DATABASE_PORT=55432` for the pytest step, and stops
      it via `trap` on exit (success or failure)
- [x] 4.3 Have the script/target print a pass/fail summary per step at the
      end of the run

## 5. `make ci` target

- [x] 5.1 Wire `make format-check` + per-package `ruff check` (reusing
      `RUFF_PACKAGES`) as the first step
- [x] 5.2 Wire the frontend step: `npm ci`, `npm test -- --run`,
      `npm run build`, `npm run lint` (with the same explicit sibling-package
      paths `frontend-checks.yml` passes to `oxlint`)
- [x] 5.3 Wire the backend step: `pytest -m "not e2e"` against the `.ci/`
      PostgreSQL, invoked the same way `uv run --project core/backend pytest`
      is invoked elsewhere post-migration
- [x] 5.4 Wire `check_migration_boundaries`
- [x] 5.5 Wire `django_safe_migrations.cli --baseline core/backend/.migration-baseline.json`
- [x] 5.6 Add the `ci` target to `.PHONY` and to the `help` listing

## 6. De-duplication and docs

- [x] 6.1 Make `RUFF_PACKAGES` (or an equivalent file) the single source
      `ruff.yml` and the `Makefile` both reference
- [x] 6.2 Document `make ci` in the root README (prerequisites: Docker,
      `uv`, Node; what it does and does not check, pointing at CI for the
      rest)

## 7. Verification

- [x] 7.1 Run `make ci` on a clean checkout end-to-end; confirm it passes
- [x] 7.2 Deliberately break a step (e.g. a ruff violation, a failing test,
      a destructive migration) one at a time; confirm `make ci` reports the
      right failing step and exits non-zero
- [x] 7.3 Confirm `make ci` and `make dev-up` can run concurrently without
      port or data collisions
