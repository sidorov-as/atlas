#!/usr/bin/env bash
# `make ci`'s orchestrator: starts a throwaway PostgreSQL (.ci/docker-compose.yml),
# runs the checks wired in below via `run_step`, always stops that PostgreSQL
# afterward regardless of outcome, and prints a pass/fail summary per step.
#
# Published on CI_POSTGRES_PORT (default 55432) under its own Compose project
# name, distinct from docker-compose.dev.yml's port (5432) and project name,
# so this can run alongside a running `make dev-up` dev stack without a port
# or data clash (see .ci/docker-compose.yml).
set -euo pipefail
cd "$(dirname "$0")/.."
repo_root="$PWD"

# uv always uses the project's own .venv here; an unrelated activated venv
# (e.g. pyenv-virtualenv) would only make every `uv run` warn about a mismatch.
unset VIRTUAL_ENV

CI_POSTGRES_PORT="${CI_POSTGRES_PORT:-55432}"
export CI_POSTGRES_PORT
export DJANGO_DATABASE_HOST="${DJANGO_DATABASE_HOST:-localhost}"
export DJANGO_DATABASE_PORT="$CI_POSTGRES_PORT"

compose_ci() { docker compose -f .ci/docker-compose.yml -p atlas-ci "$@"; }

summary_file=$(mktemp)
cleanup() {
  echo ""
  echo "==> Stopping .ci/ postgres"
  compose_ci down --volumes >/dev/null
  rm -f "$summary_file"
}
trap cleanup EXIT

echo "==> Starting .ci/ postgres (port ${CI_POSTGRES_PORT})"
compose_ci up --wait

failed=0

# Runs one `make ci` check, records its pass/fail for the closing summary,
# and keeps going on failure so a single failing step doesn't hide the
# verdict of the steps after it.
run_step() {
  local name="$1"
  shift
  echo ""
  echo "==> ${name}"
  if "$@"; then
    printf 'PASS\t%s\n' "$name" >>"$summary_file"
  else
    printf 'FAIL\t%s\n' "$name" >>"$summary_file"
    failed=1
  fi
}

# RUFF_PACKAGES is exported by the Makefile's `ci` target, so this is the
# only place besides the Makefile itself that needs the package list — it's
# not duplicated here.
run_lint() {
  make format-check || return 1
  local p
  for p in $RUFF_PACKAGES; do
    echo "ruff check ${p}"
    uvx ruff check "$p" || return 1
  done
}

# Same commands frontend-checks.yml runs, in the same order, including its
# explicit absolute sibling-package paths for oxlint (oxlint's own scope is
# only its cwd — it doesn't follow imports or workspace config — and it
# rejects ".."-relative paths, hence absolute).
run_frontend() {
  npm ci || return 1
  (cd core/frontend && npm test -- --run) || return 1
  (cd core/frontend && npm run build) || return 1
  (cd core/frontend && npm run lint -- \
    src \
    "${repo_root}/plugin-api/typescript/src" \
    "${repo_root}/plugins/standard-catalog/frontend/src" \
    "${repo_root}/plugins/apis/frontend/src" \
    "${repo_root}/plugins/c4/frontend/src" \
    "${repo_root}/plugins/database-schema/frontend/src" \
    "${repo_root}/plugins/flows/frontend/src") || return 1
}

# Invoked the same way backend-tests.yml invokes it: from the repo root (not
# core/backend), which is where pytest.ini's rootdir requires cwd to be.
# `-m "not e2e"` deselects the one test needing Docker for itself (see
# pytest.ini's `e2e` marker); CI's own backend-tests job runs the full,
# unfiltered suite and still covers it.
run_backend_pytest() {
  uv run --project core/backend pytest -m "not e2e"
}

# Dependency-free (no Docker, no git ref) — same invocation migration-lint.yml
# uses, just from core/backend instead of $GITHUB_WORKSPACE.
run_check_migration_boundaries() {
  (cd core/backend && uv run python manage.py check_migration_boundaries)
}

# `--baseline`, not `--diff origin/${{ base_ref }}`: the exact same command,
# against the exact same committed file, run locally and in CI (see
# migration-lint.yml), so the two can't disagree about a migration's
# destructive-operation verdict because of an unfetched or missing
# origin/main. DJANGO_SETTINGS_MODULE is exported explicitly because this
# runs the CLI directly (`-m django_safe_migrations.cli`), not through
# manage.py, which is the one thing that defaults it for us.
run_migration_safety_check() {
  (cd core/backend && DJANGO_SETTINGS_MODULE=server.settings \
    uv run python -m django_safe_migrations.cli --baseline .migration-baseline.json)
}

# `mcp/` is a separate, uncomposed project (design.md Decision 7: it holds
# no Django import and isn't part of `core/backend`'s own `uv sync`), so it
# gets its own pytest invocation here rather than riding along with
# `run_backend_pytest` above. Run from `mcp/` itself (like `mcp-tests.yml`'s
# `working-directory: mcp`): from the repo root, pytest would pick up the root
# `pytest.ini` (Django settings, `core/backend/conftest.py`) instead of
# stopping at `mcp/pyproject.toml`.
run_mcp_pytest() {
  (cd mcp && uv run pytest)
}

# Build-only, matching `mcp-tests.yml`'s own `docker-build` job: this
# repository does not publish or version this image (design.md's
# Non-Goals), so there is no push step to mirror here either.
run_mcp_docker_build() {
  docker build -t atlas-mcp:ci-local mcp
}

run_step "ruff + format-check" run_lint
run_step "frontend (test/build/lint)" run_frontend
run_step "backend pytest" run_backend_pytest
run_step "mcp/ pytest" run_mcp_pytest
run_step "mcp/ docker build" run_mcp_docker_build
run_step "check_migration_boundaries" run_check_migration_boundaries
run_step "migration safety check" run_migration_safety_check

echo ""
echo "==> Summary"
if [ -s "$summary_file" ]; then
  while IFS=$'\t' read -r result name; do
    printf "  %-6s %s\n" "$result" "$name"
  done <"$summary_file"
else
  echo "  (no steps wired in yet)"
fi

exit "$failed"
