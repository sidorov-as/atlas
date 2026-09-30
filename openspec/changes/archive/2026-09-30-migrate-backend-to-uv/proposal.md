## Why

`core/backend`'s `poetry.lock` is the single dependency resolution for the
whole backend workspace: `core/backend/pyproject.toml` declares `composer`,
`plugin-api/python`, and all eight `plugins/*/backend` packages as
`develop = true` path dependencies, so one `poetry install` builds the one
shared virtualenv that the repo-root `pytest.ini` needs (its `testpaths` span
`core/backend` and every plugin backend in a single collection run).

This makes the backend dependency workflow fragile in a way that is
independent of which Python version is installed. Poetry's own CLI is
commonly installed through `pipx`, precisely so its runtime is isolated from
any project's local Python-version pin — but when that isolation breaks (a
stale/misdirected `pipx` symlink, or Poetry installed through a
pyenv-managed interpreter instead), Poetry's `requires-python` check runs
against Poetry's *own* interpreter and can reject every command — including
`poetry env use`, the command meant to fix exactly that mismatch — even when
a correct, already-provisioned virtualenv sits right next to it. This was
reproduced locally: a `core/backend/.venv` already built against the
project's pinned Python was present and unused, while `poetry run`/`poetry
env use` both failed with the same `requires-python` error, because Poetry's
own executable was resolving through a different, incompatible interpreter.

`uv` does not have this failure mode: it ships as a single static binary,
manages its own Python interpreters directly (`uv python install`), and
never depends on a project's `.python-version` or any system Python to run
its own commands. The project has already adopted `uv` for `composer`,
`docs-site`, and `plugins/auth-gitea/backend` (each with its own `uv.lock`),
and the root `Makefile` already assumes `uv`/`uvx` exclusively — it never
invokes `poetry`. `core/backend` and the remaining Poetry-only packages are
the last holdout of a second, parallel toolchain.

Migrating this workspace to `uv` removes the whole class of
self-referential tool-installation fragility, and is a prerequisite for a
reliable local `make ci` (a planned follow-up change) that needs one
dependency workflow to install and run against, not two.

## What Changes

- Convert `core/backend`, `plugin-api/python`, and each Poetry-only plugin
  backend (`apis`, `auth-oidc`, `c4`, `database-schema`, `flows`,
  `ingestion`, `standard-catalog`) from Poetry (`poetry-core` build backend,
  `[tool.poetry.dependencies]`, `poetry.lock`) to `uv`
  (`[project.dependencies]`/`[dependency-groups]`, `[tool.uv.sources]` for
  the editable path dependencies, `uv.lock`), following the pattern already
  in use by `composer`, `docs-site`, and `plugins/auth-gitea/backend`.
- Replace `core/backend/poetry.lock` and `core/backend/poetry.toml` with a
  single `uv.lock` that resolves `core/backend` plus every plugin backend as
  workspace members, preserving the one-shared-virtualenv property that
  `pytest.ini`'s cross-plugin `testpaths` collection depends on.
- **BREAKING** (build/deploy only, not runtime): rewrite
  `core/backend/Dockerfile`'s dependency-install stage from
  `pip install poetry` + `poetry install` to `uv sync --frozen`, for both the
  `development` and production build targets. The resulting image's Python
  dependency set and application behavior are unchanged; only the tool used
  to produce the image changes.
- Update the four GitHub Actions workflows that currently do
  `pipx install poetry && poetry install` in `core/backend`
  (`backend-tests`, `migration-lint`, `dependency-audit`,
  `authentication-examples-integration`) to use the existing reusable
  `.github/actions/setup-python-env` composite action (`uv sync --frozen`),
  the same action already used by `authentication-examples-fast` and
  `pages.yml`.
- Update `pip-audit`'s `dependency-audit` job to point at the `uv`-managed
  virtualenv location instead of `core/backend/.venv` created by
  `poetry.toml`'s `in-project = true` (uv's default `.venv` location is
  compatible, but the job's install step changes).
- Remove `core/backend/poetry.toml` (in-project venv config) and the
  `poetry-core` build-system declaration from every migrated
  `pyproject.toml`.

Out of scope: `examples/authentication/custom-credentials/plugin`'s own
Poetry setup (a standalone example plugin, not part of the shared backend
workspace) is not touched by this change.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `backend-platform-foundation`: the "Template-aligned backend foundation"
  requirement currently commits to adopting the upstream
  `wemake-django-template` revision's dependency workflow (Poetry) as-is.
  This change introduces an explicit, documented departure from that
  inherited dependency workflow in favor of `uv`, while preserving every
  other template-aligned property (application layout, settings
  architecture, Docker runtime, operational configuration).

## Impact

- **Code**: 9 `pyproject.toml` files (`core/backend`, `plugin-api/python`,
  7 plugin backends), `core/backend/poetry.lock` → `uv.lock`,
  `core/backend/poetry.toml` (removed), `core/backend/Dockerfile`.
  **Found during implementation**: `composer/atlas_composer/resolver.py` reads
  `core/backend/poetry.lock` at runtime to resolve deployment-manifest plugin
  versions/hashes — not mentioned above originally. Replaced
  `composer/atlas_composer/poetry_lock.py` with `uv_lock.py` (parses `uv.lock`
  instead); see design.md's Risks section.
  **Also found during implementation**: `deploy/render/Dockerfile`, a second
  production build path explicitly documented to mirror
  `core/backend/Dockerfile`, had its own `poetry install` stage and its own
  `COPY core/backend/poetry.lock`. Migrated it the same way; see design.md's
  Risks section.
  **Build backend**: all 9 files also dropped `poetry-core` for `uv_build`
  (uv's own PEP 517 backend) rather than staying on Poetry's build backend
  indefinitely — the spec's acceptance scenario requires no `poetry-core`
  declaration anywhere, and `uv_build` keeps the whole toolchain on `uv`
  rather than introducing a third-party build backend.
- **CI**: `.github/workflows/backend-tests.yml`,
  `migration-lint.yml`, `dependency-audit.yml`,
  `authentication-examples-integration.yml`.
- **Deployment**: the production image build (`core/backend/Dockerfile`,
  used by `docker-compose.dev.yml` and the production Compose topology)
  changes its dependency-install stage. Runtime behavior and the resulting
  installed package set are unchanged.
- **Developer workflow**: `poetry install`/`poetry run` at `core/backend`
  is replaced by `uv sync`/`uv run`; onboarding docs referencing Poetry need
  updating.
- **Not affected**: `composer`, `docs-site`, `plugins/auth-gitea/backend`
  (already on `uv`), and `examples/authentication/custom-credentials/plugin`
  (standalone, out of scope).
