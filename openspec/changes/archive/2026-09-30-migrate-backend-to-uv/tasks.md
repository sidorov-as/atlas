## 1. `plugin-api/python`

- [x] 1.1 Convert `plugin-api/python/pyproject.toml` from `[tool.poetry.dependencies]`
      to `[project.dependencies]`/`[dependency-groups]`, keep `requires-python`
- [x] 1.2 Run `uv lock` inside `plugin-api/python`, verify `uv sync` succeeds
- [x] 1.3 Run that package's own test suite (if any) against the new env
      (deferred: `atlas_plugin_api`'s tests need `DJANGO_SETTINGS_MODULE=server.settings`
      configured at class-definition time via `django-modern-rest`'s `Controller`, which
      only exists in `core/backend`'s shared venv — same one-shared-virtualenv property
      documented in design.md Decision 1. Verified instead: `uv sync` builds and installs
      the package, and `uv run python -c "import atlas_plugin_api"` succeeds. Real test
      execution happens in 3.5 once the workspace-wide `uv.lock` exists.)

## 2. Plugin backends (independent of each other; depend only on plugin-api/python)

- [x] 2.1 Convert `plugins/apis/backend/pyproject.toml` to uv
- [x] 2.2 Convert `plugins/auth-oidc/backend/pyproject.toml` to uv
- [x] 2.3 Convert `plugins/c4/backend/pyproject.toml` to uv
- [x] 2.4 Convert `plugins/database-schema/backend/pyproject.toml` to uv
- [x] 2.5 Convert `plugins/flows/backend/pyproject.toml` to uv
- [x] 2.6 Convert `plugins/ingestion/backend/pyproject.toml` to uv
      (also depends on `atlas-plugin-standard-catalog` and `atlas-plugin-apis` as path
      dependencies, not just `plugin-api/python` — both got their own `[tool.uv.sources]`
      entries too, not covered by this task's own wording)
- [x] 2.7 Convert `plugins/standard-catalog/backend/pyproject.toml` to uv
- [x] 2.8 For each, add `[tool.uv.sources]` pointing at `../../../plugin-api/python`
      (editable), confirm `uv sync` succeeds standalone for each package
      (verified: `uv lock` + `uv sync` succeed standalone for all 7, ingestion included)

## 3. `core/backend` workspace root

- [x] 3.1 Convert `core/backend/pyproject.toml`'s `[tool.poetry.dependencies]`
      path entries (composer, plugin-api/python, and all 8 plugin backends)
      to `[tool.uv.sources]` editable entries
- [x] 3.2 Move third-party dependencies to `[project.dependencies]` and dev
      dependencies to `[dependency-groups.dev]`
- [x] 3.3 Run `uv lock` from `core/backend/`, producing the workspace-wide
      `uv.lock`
      (81 packages resolved)
- [x] 3.4 Diff resulting package versions against current `poetry.lock`;
      flag and resolve any drift that changes tested behavior
      (diffed all 81 vs. 80 poetry.lock entries: only minor/patch bumps within
      already-declared ranges — e.g. `django` 6.1→6.1.1, `mypy` 1.19.1→1.20.2 —
      plus `atlas-backend` itself newly appearing (uv always lists the
      workspace root; poetry.lock didn't since `package-mode = false`).
      Nothing crossed a declared constraint; no pin needed.)
- [x] 3.5 From the repo root, run `uv run --project core/backend pytest`
      and confirm the full cross-plugin suite (per `pytest.ini` testpaths)
      collects and passes
      (1370 passed)
- [x] 3.6 Remove `core/backend/poetry.toml`
      (also removed `core/backend/poetry.lock` here, once 3.6a below unblocked it —
      not itemized by this task's own wording, but required by the proposal/spec's
      "no poetry.lock ... present" scenario)

### 3a. Unplanned: `composer` read `core/backend/poetry.lock` directly (found during 3.6)

Not covered by the original proposal/design — see design.md's Risks section for
the full writeup. `composer/atlas_composer/resolver.py` cross-references
deployment-manifest plugin versions/hashes against `core/backend/poetry.lock` at
runtime, not just in tests; deleting the file per this change's own "no
poetry.lock present" requirement would have silently broken manifest resolution.

- [x] 3a.1 Add `composer/atlas_composer/uv_lock.py` (`parse_uv_lock`), reading
      `uv.lock`'s shape (`source.registry` + `wheels`/`sdist` hashes; `source.editable`/
      `source.directory` + computed directory hash for workspace packages)
- [x] 3a.2 Point `resolver.py`'s `NativeLocks.from_repo_root` at
      `core/backend/uv.lock` instead of `poetry.lock`
- [x] 3a.3 Remove `composer/atlas_composer/poetry_lock.py` and
      `tests/test_poetry_lock.py`; add `tests/test_uv_lock.py` against
      `core/backend/uv.lock`
- [x] 3a.4 Fix stale `poetry.lock` mentions in `manifest.py`'s docstring and
      `cli.py`'s `--repo-root` help text
- [x] 3a.5 Re-run the full repo-root suite (1370 passed) and `composer`'s own
      suite (113 passed) with `poetry.lock`/`poetry.toml` actually gone

## 4. `core/backend/Dockerfile`

- [x] 4.1 Replace the `pip install poetry` / `poetry install` install stage
      with `uv sync --frozen` (installing `uv` itself per its documented
      Docker install method)
      (installed via `COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /usr/local/bin/`,
      pinned to match this repo's local uv version. Also switched to
      `UV_PROJECT_ENVIRONMENT=/usr/local` instead of a project-local `.venv` — found that
      `docker-compose.dev.yml` bind-mounts `./core/backend` and each plugin's source dir
      over their `/code/...` paths in the `development` target, which would shadow a
      `.venv` built at `/code/core/backend/.venv`. Installing into the system Python
      instead mirrors Poetry's own `POETRY_VIRTUALENVS_CREATE=false` behavior and needs
      no `PATH` change. Also had to drop `core/backend/uv.lock` from `.dockerignore` —
      it was excluding the very file the new install stage `COPY`s in.)
- [x] 4.2 Build and smoke-test the `development` target
      (`docker compose -f docker-compose.dev.yml up --build`)
      (built and ran via `docker compose -f docker-compose.dev.yml up -d --build postgres
      migrate backend`: migrate exited 0, backend container reports `(healthy)`,
      `/healthz/` returns 200, and an editable install resolves back to the bind-mounted
      source path, confirming live-edit still works)
- [x] 4.3 Build and smoke-test the production target manually
      (`docker build --target production --build-arg DJANGO_ENV=production`, run against
      the existing postgres container: gunicorn boots, `/healthz/` returns 200, and
      dev-only tooling — pytest/mypy/ruff — is confirmed absent from the image)

## 5. CI workflows

- [x] 5.1 `backend-tests.yml`: replace `pipx install poetry` + `poetry install`
      with the `setup-python-env` composite action; replace
      `poetry -P core/backend run pytest` with `uv run --project core/backend pytest`
      (verified locally: 1370 passed, matching 3.5)
- [x] 5.2 `migration-lint.yml`: same install-step replacement; update the
      `poetry run` invocations to `uv run`
      (verified locally: both steps pass — no migration issues found, no
      cross-plugin migration dependency violations)
- [x] 5.3 `dependency-audit.yml`: same install-step replacement; verify and
      update `pypa/gh-action-pip-audit`'s `virtual-environment` input to
      match uv's `.venv` location
      (verified: `uv sync`'s default in-project venv lands at the same
      `core/backend/.venv` path Poetry's `poetry.toml` used — the
      `virtual-environment` input needed no path change)
- [x] 5.4 `authentication-examples-integration.yml`: same install-step
      replacement for its Poetry-based plugin install step
      (only `security-negative-journeys`; the matrix `integration` job is
      Docker Compose-based and doesn't touch Poetry. Verified locally: all 9
      security-negative tests pass under `uv run`)

## 6. Cleanup and verification

- [x] 6.1 Remove every remaining `[build-system] requires = ["poetry-core"...]`
      block from the 9 migrated `pyproject.toml` files
      (replaced with `uv_build` — uv's own PEP 517 backend — rather than
      leaving Poetry's build backend in place or picking a third-party one;
      see proposal.md's Impact and design.md's Risks. `plugin-api/python`
      needed an explicit `module-name` override (its distribution name has an
      extra `-python` suffix the module name doesn't); all 8 packages needed
      `module-root = ""` for their flat (non-`src/`) layout. `core/backend`
      has `[tool.uv] package = false` already — never built, so no build
      backend needed at all; both `[build-system]` and `[tool.poetry]`
      removed outright. Verified: `uv lock`/`uv sync` succeed standalone for
      all 8 packages and for the `core/backend` workspace.)
- [x] 6.2 Update any onboarding docs/README sections that reference
      `poetry install`/`poetry run` for backend setup
      (16 docs-site pages, `CONTRIBUTING.md`, `core/backend/README.md`,
      `openspec/specs/containerized-runtime/spec.md` — the last one because
      it now describes the actual `core/backend/Dockerfile` install command
      — plus `distributions/default/manifest.yaml`, `deploy/render/
      manifest.yaml`, and `docs-site/examples/first-plugin/.../example.yaml`,
      all referencing `core/backend/poetry.lock` or `poetry run`. Verified
      with the full `authentication-examples-fast.yml` validator suite
      (docs-accuracy, syntax, schemas, imports, compose, content, workflows —
      all pass) plus docs-site's own `validate_docs.py`/`test_validate_docs.py`.
      Found the `secrets` validator already failing on `main`, unrelated to
      any file this change touches — flagged, not fixed, out of scope.)
- [x] 6.3 Full repo-root `uv run pytest` (or equivalent) green, ruff/mypy
      still pass against the migrated packages, both Docker targets build
      (pytest: 1370 passed. ruff: all checks passed. mypy: 77 pre-existing
      errors in `seed_booking_demo.py`/`entity_service.py`, confirmed
      byte-identical under the exact original Poetry-locked mypy/django-stubs
      versions too — pre-existing tech debt, not migration-caused, and no CI
      workflow enforces mypy today; left as-is. Both `core/backend/Dockerfile`
      targets rebuilt and smoke-tested again after the `uv_build` switch.
      `deploy/render/Dockerfile`, found during this task (see 6.1's note and
      design.md), also rebuilt and smoke-tested end-to-end.)
