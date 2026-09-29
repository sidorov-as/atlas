## Why

A prerelease audit found CI does not actually verify the project: today's four workflows (`authentication-examples-fast.yml`, `authentication-examples-integration.yml`, `migration-lint.yml`, `pages.yml`) cover authentication examples, a narrow slice of security-negative backend tests, migration safety, and docs publishing — but no workflow runs the full backend pytest suite, no workflow runs frontend test/build/lint, no workflow runs Ruff, no workflow runs `npm audit` or `pip-audit`, and no workflow runs a secret scanner (verified by reading `.github/workflows/*.yml` directly; confirmed no Gitleaks config exists anywhere in the repo — the audit's Gitleaks results were a one-off manual scan, not a standing CI gate). Separately, every third-party GitHub Action is pinned to a mutable version tag (`actions/checkout@v4`, `actions/setup-python@v5`, `astral-sh/setup-uv@v6`, `actions/upload-artifact@v4`, `actions/upload-pages-artifact@v3`, `actions/deploy-pages@v4`), and no Dependabot/Renovate config exists to track or bump those pins. A public repository whose CI doesn't actually gate its own quality claims, and whose CI definition trusts mutable upstream tags, is both a correctness risk and a supply-chain risk.

## What Changes

- Add a CI workflow that runs the full backend pytest suite across `core/backend` and every plugin backend (not just the security-negative subset already run in `authentication-examples-integration.yml`).
- Add a CI workflow that runs frontend test, build, and lint for `core/frontend` (and any other frontend packages under `plugins/*/frontend` if they exist and have their own scripts).
- Add a CI workflow that runs `ruff check` per Python package, against each package's own `pyproject.toml` configuration.
- Add a CI workflow (or job) that runs `npm audit --audit-level=high` for frontend packages and `pip-audit` for Python packages.
- Add a CI workflow (or job) that runs a secret scan (Gitleaks) over the repository/PR diff — this is new, not a tightening of an existing job.
- Pin every third-party GitHub Action reference (in `.github/workflows/*.yml` and `.github/actions/*/action.yml`) to a full commit SHA, with a trailing comment noting the human-readable version for reviewability.
- Add a Dependabot (or Renovate) configuration covering GitHub Actions, so SHA pins get proposed bumps instead of silently going stale.
- Sequence the new gates so they become required only once what they check is actually green (see design.md) — this change does not itself fix Ruff violations, frontend vulnerabilities, or backend test failures; it depends on `ruff-cleanup` and `fix-frontend-dependency-vulnerabilities` (separate changes) landing first, or ships its new checks in reporting-only mode until they do.

## Capabilities

### New Capabilities

- `ci-quality-gates`: Required CI checks (backend tests, frontend tests/build/lint, Ruff, dependency audit, secret scan) that must pass before a change merges, plus supply-chain pinning of the CI definition itself (GitHub Actions pinned to commit SHA with automated bump PRs).

### Modified Capabilities

None — no existing capability in `openspec/specs/` covers CI pipeline behavior (checked `backend-platform-foundation` and `deployment-manifest-and-lock`; both describe runtime/deployment behavior of the application itself, not the CI process that verifies it).

## Impact

- Adds new files under `.github/workflows/` (e.g. `backend-tests.yml`, `frontend-checks.yml`, `lint.yml` or similar — exact filenames are an implementation decision, not fixed by this proposal) and a `.github/dependabot.yml`.
- Modifies every existing `.github/workflows/*.yml` and `.github/actions/*/action.yml` to replace mutable tag references with commit SHAs.
- No application code is touched by this change.
- Depends on `ruff-cleanup` and `fix-frontend-dependency-vulnerabilities` (separate changes) for the Ruff and frontend-audit gates to be meaningful as *required* (not just present) checks — see design.md for how this change handles that ordering.
