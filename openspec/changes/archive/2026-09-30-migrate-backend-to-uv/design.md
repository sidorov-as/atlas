## Context

`core/backend/pyproject.toml` declares `composer`, `plugin-api/python`, and
all eight `plugins/*/backend` packages as `develop = true` path
dependencies. `core/backend/poetry.lock` is therefore the *only* lock file
in the repo that resolves this whole workspace, and the resulting
`core/backend/.venv` (in-project, per `core/backend/poetry.toml`) is the one
environment the repo-root `pytest.ini` needs — its `testpaths` fans a single
`pytest` invocation out across `core/backend` and every plugin backend, and
per that file's own header comment, fixture ancestry breaks unless all of
those paths resolve inside one `rootdir`-relative collection against one
environment.

Three packages already use `uv` standalone, each with its own `uv.lock`:
`composer`, `docs-site`, and `plugins/auth-gitea/backend`. `composer`'s
`pyproject.toml` already demonstrates the exact mechanism this migration
needs at small scale:

```toml
[tool.poetry.dependencies]
atlas-plugin-api-python = { path = "../plugin-api/python", develop = true }

[tool.uv.sources]
atlas-plugin-api-python = { path = "../plugin-api/python", editable = true }
```

i.e. `composer` already carries *both* a Poetry-style path dependency and a
`uv`-style source for the same package — evidence that `uv` can resolve
this repo's editable-path-dependency graph today, just not yet for the
9-package `core/backend` workspace.

The root `Makefile` already never calls `poetry` — `format`/`format-check`
use `uvx ruff`, and `docs`/the `COMPOSE` variable use `uv run`. `poetry` is
invoked only from four GitHub Actions workflows and from
`core/backend/Dockerfile`.

## Goals / Non-Goals

**Goals:**
- Replace Poetry with `uv` as the single dependency-management tool for
  `core/backend` and its 7 Poetry-only plugin backends plus
  `plugin-api/python`, preserving the one-shared-virtualenv property
  `pytest.ini` depends on.
- Keep the resulting installed package set, and therefore application and
  test behavior, unchanged — this is a tooling migration, not a dependency
  upgrade.
- Collapse the four CI workflows currently doing
  `pipx install poetry && poetry install` onto the existing
  `setup-python-env` composite action, so CI has one Python setup path.
- Update `core/backend/Dockerfile`'s dependency-install stage to `uv sync`.

**Non-Goals:**
- Changing any dependency version pins beyond what `uv`'s resolver requires
  to produce an equivalent lock (a version drift, if any is unavoidable, is
  called out explicitly in review, not silently absorbed).
- Migrating `examples/authentication/custom-credentials/plugin`'s own,
  separate Poetry setup.
- Building `make ci` itself (tracked as a separate, dependent change).
- Changing `pytest.ini`, its `testpaths`, or any test code.

## Decisions

### Decision 1: `uv` workspace via `[tool.uv.sources]`, not a monorepo-wide `[tool.uv.workspace]`

Three approaches were considered for how `uv` should see the 9 packages:

1. **`[tool.uv.sources]` path/editable entries in `core/backend/pyproject.toml`**
   (chosen) — mirrors exactly what `composer`'s `pyproject.toml` already
   does today, just for 8 packages instead of 1. Each plugin backend stays
   an independently valid, installable package (it can still be depended on
   in isolation, e.g. by `plugins/auth-gitea/backend`'s own standalone
   `uv.lock`, unaffected by this change). One `uv.lock` at `core/backend/`
   resolves the whole graph, same shape as `poetry.lock` today.
2. **A single `[tool.uv.workspace]` spanning the whole repo** — `uv`'s
   native multi-package workspace primitive. Rejected for this change: it
   would pull `docs-site` (a `package = false` uv project with a different
   Python constraint, `>=3.12`) and every frontend-adjacent Python tool into
   one workspace root, a much larger blast radius than "migrate the backend
   test/install path off Poetry." Nothing here forecloses adopting a
   repo-wide workspace later; it is a strict superset of this change's
   result.
3. **Per-package `uv.lock` with no shared environment** (i.e. `uv sync`
   independently inside each plugin backend, matching how each package can
   already be installed alone) — rejected because it does not reproduce a
   single shared virtualenv, which `pytest.ini`'s cross-plugin collection
   requires. This would require restructuring the test suite itself, which
   is explicitly out of scope.

### Decision 2: `uv sync --frozen` in CI and in `core/backend/Dockerfile`, not `uv sync`

`--frozen` refuses to update `uv.lock` if it's out of date relative to
`pyproject.toml`, failing the install instead of silently re-resolving.
This matches the guarantee `poetry install` already provides in CI today
(Poetry also fails on a stale lock unless told to update it) and is the same
flag the existing `setup-python-env` composite action already uses for
`composer`, `docs-site`, and `auth-gitea`'s standalone installs — so this
is consistency with an established pattern, not a new one.

### Decision 3: Regenerate the lock, don't hand-translate `poetry.lock` to `uv.lock`

`uv.lock` and `poetry.lock` are different, tool-owned formats; there is no
supported converter between them. The lock is regenerated from the migrated
`pyproject.toml` files via `uv lock`, and the resulting dependency versions
are diffed against the current `poetry.lock` as a review step (see Risks).

## Risks / Trade-offs

- **[Risk, found during implementation] `composer` reads `core/backend/poetry.lock`
  directly at runtime.** `composer/atlas_composer/resolver.py` cross-references
  deployment-manifest plugin versions/hashes against `core/backend/poetry.lock`'s
  own TOML shape (`poetry_lock.py`), a real production dependency undocumented
  elsewhere in this change — not just a test fixture. Removing `poetry.lock` per
  this change's own proposal ("no poetry.lock ... present") would silently break
  `composer`'s manifest resolution. → **Resolution**: added
  `composer/atlas_composer/uv_lock.py` (`parse_uv_lock`), parsing `uv.lock`'s
  shape instead (`source.registry` + `wheels`/`sdist` hashes for registry
  packages; `source.editable`/`source.directory` + a computed directory hash
  for workspace path packages, same as before). `resolver.py` now reads
  `core/backend/uv.lock`; `poetry_lock.py` and its test were removed, replaced
  by `uv_lock.py` and `test_uv_lock.py`.
- **[Risk, found during implementation] `deploy/render/Dockerfile` is a second,
  undocumented production build path with its own `poetry install` stage.**
  Its own header comment says it "mirrors `core/backend/Dockerfile` — keep
  them in sync," and it directly `COPY`s `core/backend/poetry.lock`. Neither
  file appears anywhere in this change's original proposal/design/tasks (only
  `core/backend/Dockerfile` was listed under Impact). Removing `poetry.lock`
  would have silently broken it the next time Render (or a maintainer)
  rebuilds it. → **Resolution**: mirrored the same `core/backend/Dockerfile`
  fix here — pinned `uv` static-binary `COPY --from`, `UV_PROJECT_ENVIRONMENT=
  /usr/local`, `uv sync --frozen --no-dev`, `COPY core/backend/uv.lock`
  instead of `poetry.lock`. Verified with a full `docker build` (this
  Dockerfile bakes migrations + demo-seed + collectstatic at build time, so a
  successful build is a strong end-to-end check) and a runtime smoke test.
- **[Risk] Dependency version drift.** `uv`'s resolver is not guaranteed to
  produce byte-identical version selections to Poetry's for the same
  constraints. → **Mitigation**: diff `uv lock`'s output against current
  `poetry.lock` versions before merging; pin any package that drifts to a
  version incompatible with what's tested, if the resolver's default choice
  changes observed behavior.
- **[Risk] `core/backend/Dockerfile` is the production build path.** A
  mistake here is user-visible (broken prod image), not just a CI
  inconvenience. → **Mitigation**: build and smoke-test both the
  `development` and production Dockerfile targets locally
  (`docker compose -f docker-compose.dev.yml up --build`, plus a manual
  production-target build) before merging; keep the change to the
  install-stage commands only, not the multi-stage structure.
- **[Risk] `dependency-audit`'s `pip-audit` step currently points at
  `core/backend/.venv`** (an artifact of `poetry.toml`'s
  `in-project = true`). → **Mitigation**: `uv sync` also defaults to an
  in-project `.venv`, so the path is likely unchanged, but this is verified
  explicitly rather than assumed, since `pypa/gh-action-pip-audit`'s
  `virtual-environment` input must point at a real venv.
- **[Trade-off] Departure from `wemake-django-template` traceability.** The
  `backend-platform-foundation` spec commits to adopting the template's
  "dependency workflow" as-is; this change is a deliberate, documented
  exception (see proposal's Modified Capabilities), not an oversight.

## Migration Plan

1. Migrate `plugin-api/python` first (no path-dependencies of its own,
   leaf of the dependency graph) — validates the basic Poetry→uv conversion
   in isolation.
2. Migrate each of the 7 plugin backends next, in any order (each only
   depends on `plugin-api/python` and third-party packages) — each becomes
   independently `uv sync`-able, same as `auth-gitea` already is.
3. Migrate `core/backend` last: convert its `[tool.poetry.dependencies]`
   path entries to `[tool.uv.sources]`, run `uv lock` to produce the
   workspace-wide `uv.lock`, and confirm `uv run pytest` (from the repo
   root, per `pytest.ini`'s rootdir requirement) collects and passes the
   full suite.
4. Update `core/backend/Dockerfile`'s install stage.
5. Update the 4 CI workflows to use `setup-python-env`.
6. Remove `core/backend/poetry.toml` and the `poetry-core` build-system
   blocks.

Rollback: revert the commit(s); `poetry.lock` and `poetry.toml` are removed
only in the final step, so any step before that can be reverted
independently without leaving the workspace uninstallable.

## Open Questions

- None outstanding — the SSH e2e ingestion test (`docker`-dependent,
  currently inside the same `pytest` collection this migration preserves)
  is tracked as a separate, independent change and does not block or get
  blocked by this one.
