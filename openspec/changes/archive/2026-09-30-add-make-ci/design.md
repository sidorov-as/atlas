## Context

CI today runs 8 separate workflows on every PR (see the table in this
project's own working notes, not reproduced here): `backend-tests`, `ruff`,
`frontend-checks`, `migration-lint`, `authentication-examples-fast`,
`dependency-audit`, `secret-scan`, and `authentication-examples-integration`.
Of these, the first five are fast (individually well under a couple of
minutes) and require no Docker matrix or external network beyond package
installs; the last three are either matrix-based
(`authentication-examples-integration`: 5 Docker topologies), network-heavy
(`dependency-audit`), or a dedicated scanning tool
(`secret-scan`/gitleaks) with its own binary.

`make ci`'s purpose is narrowly scoped by design: give a developer the same
pass/fail verdict as the fast checks, in a single local command, fast enough
to run before every push. It is deliberately not a full local mirror of CI.

## Goals / Non-Goals

**Goals:**
- One command (`make ci`) that runs ruff, frontend test/build/lint, backend
  pytest (minus the one Docker-dependent test), and migration safety checks,
  locally, with a clear pass/fail summary per step.
- Local and CI verdicts for the migration safety check are produced by the
  literal same command against the literal same baseline file — no
  git-ref-freshness dependence in either place.
- The backend pytest step needs only `docker compose` for a throwaway
  PostgreSQL — no Docker-in-Docker, no mounted `docker.sock`.

**Non-Goals:**
- Running `authentication-examples-integration`'s Docker-topology matrix
  locally.
- Running `dependency-audit` or `secret-scan` as part of `make ci` (they
  stay CI-only; no `ci-full` variant is introduced by this change).
- Rewriting the SSH e2e ingestion test's container setup or giving it its
  own dedicated CI job — this change only adds the `pytest` marker `make ci`
  needs to exclude it; the rest is separate, future work.
- Changing what `backend-tests.yml`/`frontend-checks.yml` run in CI beyond
  what's needed to keep them the source of truth `make ci` mirrors.

## Decisions

### Decision 1: A dedicated `.ci/docker-compose.yml`, not the existing `docker-compose.dev.yml`

Three options for where the throwaway PostgreSQL comes from:

1. **A new, `make ci`-only `.ci/docker-compose.yml` with one `postgres`
   service on a dedicated port (55432)** (chosen) — isolated from the dev
   stack, so `make ci` can run alongside `make dev-up` without a port
   clash, and its lifecycle (start, wait, stop via `trap`) is scoped to a
   single `make ci` invocation rather than a long-lived dev database a
   developer might already have data in.
2. **Reuse `docker-compose.dev.yml`'s `postgres` service** — rejected: it
   binds `5432` (a developer may already have it running, and `make ci`
   dropping/reseeding its schema mid-session would be destructive to
   whatever the developer was doing in the dev stack); also the dev
   stack's `postgres` is meant to be long-lived, not started/stopped per
   `make ci` run.
3. **`testcontainers`-style ephemeral Postgres started directly by
   `pytest`** (e.g. a `pytest` fixture that spins up its own container) —
   rejected for this change: a bigger change to how the backend suite
   provisions its database for every environment (including CI, which
   today gets PostgreSQL as a GitHub Actions `services:` entry, not from
   the test process), out of proportion to what's needed here.

### Decision 2: Migration check via a committed baseline file, run identically locally and in CI

`django_safe_migrations` supports two independent axes: what's checked
(`--diff <ref>`, `--since-commit <ref>`, or nothing = everything) and what's
excluded (`--baseline <file>`). Today's `migration-lint.yml` uses
`--diff origin/${{ base_ref }}` with no baseline. This change switches both
local and CI usage to the *unscoped* check (no `--diff`/`--since-commit`,
i.e. every migration is inspected) filtered by a `--baseline` file committed
to the repo. This means:
- No git ref (`origin/main` or otherwise) is ever consulted by this check,
  locally or in CI — it cannot go stale, and a fork-workflow developer
  (`origin` = their fork) is unaffected, since nothing depends on what
  `origin` points to.
- The exact same command, against the exact same file, runs everywhere;
  local and CI verdicts cannot diverge because of environment differences.
- The baseline file needs an explicit, occasional maintenance step (pruning
  entries once the underlying migrations are no longer a concern), which is
  a one-time/periodic manual action, not a per-PR one.

Alternative considered: keep `--diff` locally but have `make ci` run
`git fetch origin "$(git symbolic-ref refs/remotes/origin/HEAD | sed
's@.*/@@')"` first to guarantee freshness. Rejected: still assumes `origin`
is the canonical repo (breaks under a fork workflow), adds a network
dependency and a new failure mode (fetch failure) to every `make ci` run,
and doesn't remove the local/CI-divergence risk as completely as baseline
mode does.

### Decision 3: Exclude the Docker-dependent test via a pytest marker, not by moving the file or containerizing `make ci`'s pytest step

Three options for handling
`test_git_connector_integration.py::test_ssh_key_auth_clone_round_trip`
(the only test needing Docker) within `make ci`:

1. **Register and apply an `e2e` pytest marker; `make ci` runs
   `pytest -m "not e2e"`** (chosen) — minimal, explicit, and consistent
   with the module's own existing self-description ("the only tests in the
   ingestion plugin's suite that need [Docker]"). CI's `backend-tests` job
   is untouched and keeps running the marked test as part of the full
   suite, so coverage is not reduced — it's just not part of the local fast
   loop.
2. **Run `make ci`'s whole backend pytest step inside a container with
   `/var/run/docker.sock` mounted, so the test runs "for real" locally
   too** — rejected: adds Docker-in-Docker plumbing to `make ci`'s critical
   path for the sake of one test, and nests a container topology that
   doesn't match how CI actually runs it (CI runs directly on the runner's
   host Docker, not nested).
3. **Leave the test unmarked and let it self-skip when Docker isn't
   reachable from wherever `make ci`'s pytest runs** — rejected: today's
   `skipif(not _docker_available())` means the test's fate depends on
   incidental environment details (is Docker on PATH from inside whatever
   process runs pytest?), which is silent and non-deterministic across
   machines — exactly the ambiguity a marker resolves explicitly.

## Risks / Trade-offs

- **[Risk] Baseline file goes stale/bloated.** Nothing forces pruning it as
  historical issues are actually fixed. → **Mitigation**: documented as a
  known, accepted trade-off (see proposal); not solved by this change.
- **[Risk] `e2e` marker is forgotten on a future Docker-dependent test.**
  → **Mitigation**: the marker is registered in `pytest.ini` with a
  docstring-level explanation; `backend-tests.yml`'s own full-suite run is
  unaffected either way, so a forgotten marker fails safe (test still runs
  in CI, just also runs — and may flake — locally), not silently skipped.
- **[Trade-off] `make ci` does not catch everything CI catches.** A change
  that's fine locally can still fail `authentication-examples-integration`,
  `dependency-audit`, or `secret-scan` in CI. This is accepted scope, stated
  explicitly in the proposal's Non-Goals, not a gap to close later by
  default.

## Migration Plan

1. Land `migrate-backend-to-uv` first (this change's backend pytest step
   assumes one working `uv`-based install path).
2. Add the `e2e` marker and apply it; confirm `backend-tests.yml` is
   unaffected (still runs everything).
3. Generate and commit the migration baseline file; switch
   `migration-lint.yml` to `--baseline`; confirm CI's migration-lint job
   still passes/fails on the same PRs it did before, for the right reasons.
4. Add `.ci/docker-compose.yml` and the Make plumbing to start/stop it.
5. Add the `make ci` target wiring the steps together with a summary.
6. Unify `RUFF_PACKAGES` between the `Makefile` and `ruff.yml`.

Rollback: each step is independently revertible; `migration-lint.yml`'s
switch to `--baseline` is the only step with CI-visible behavior change and
can be reverted on its own without touching `make ci`.

## Open Questions

- None outstanding for this change's scope. Whether/when to invest in
  `testcontainers` + a dedicated e2e CI job for the ingestion SSH test is
  intentionally deferred to separate, future work.
