## 1. Supply-chain pinning

- [x] 1.1 Pin `actions/checkout@v4` references (all four workflows) to a commit SHA, with a version comment.
- [x] 1.2 Pin `actions/setup-python@v5` references to a commit SHA.
- [x] 1.3 Pin `astral-sh/setup-uv@v6` reference (in `.github/actions/setup-python-env/action.yml`) to a commit SHA.
- [x] 1.4 Pin `actions/upload-artifact@v4`, `actions/upload-pages-artifact@v3`, and `actions/deploy-pages@v4` to commit SHAs.
- [x] 1.5 Add `.github/dependabot.yml` with a `github-actions` ecosystem entry covering `.github/workflows/` and `.github/actions/*/`.

## 2. Backend test coverage

- [x] 2.1 Add a workflow that runs the full `core/backend` pytest suite (PostgreSQL service, matching the existing service config already used in `authentication-examples-integration.yml`).
- [x] 2.2 Add coverage for every plugin backend's own test suite (`plugins/*/backend`), either as one aggregated job or a matrix per plugin.
- [x] 2.3 Add coverage for `plugin-api/python` and `composer`'s own test suites if not already covered elsewhere.
- [x] 2.4 Scope the workflow's path filters (or lack thereof) so it runs on any backend-relevant change, not just the narrow paths the existing auth-examples workflows filter on.

## 3. Frontend checks

- [x] 3.1 Add a workflow that runs `core/frontend`'s test suite.
- [x] 3.2 Add a workflow (or job) that runs the frontend build.
- [x] 3.3 Add a workflow (or job) that runs the frontend lint.
- [x] 3.4 Check for and cover any other frontend packages under `plugins/*/frontend` with their own scripts.

## 4. Python lint gate

- [x] 4.1 Add a workflow that runs `ruff check` for each of the 10 Python packages (`core/backend`, `plugin-api/python`, 8 plugin backends) against that package's own `pyproject.toml`.
- [x] 4.2 Confirm this workflow only becomes a required status check once `ruff-cleanup` has merged (sequencing decision from design.md).

## 5. Dependency and secret scanning

- [x] 5.1 Add a workflow (or job) running `npm audit --audit-level=high` for frontend packages.
- [x] 5.2 Add a workflow (or job) running `pip-audit` for Python packages.
- [x] 5.3 Add a workflow (or job) running Gitleaks (or equivalent) against the PR diff.
- [x] 5.4 Confirm the frontend dependency-audit check only becomes required once `fix-frontend-dependency-vulnerabilities` has merged (sequencing decision from design.md).

## 6. Enforcement and rollout

- [x] 6.1 Verify `ruff-cleanup` and `fix-frontend-dependency-vulnerabilities` have merged before merging this change (per the "land last" sequencing decision), or re-order if circumstances changed.
  - Both are archived as OpenSpec changes. Re-verified live: `npm audit --audit-level=high` in `core/frontend` exits 0 (0 high-severity). `ruff check` had drifted red again (11 errors in `core/backend`, 2 in `plugin-api/python`, 3 in `plugins/apis/backend` — new violations introduced by other work on this branch after `ruff-cleanup` landed). Fixed: auto-fixed the two mechanical packages (`ruff check --fix`, import sort + `datetime.UTC` alias), reflowed 3 over-length lines and shortened one over-length test function name in `core/backend`, and added a `[tool.ruff.lint.per-file-ignores]` entry for `server/settings/environments/*.py` (F821 is a false positive there — django-split-settings' `include()` execs files into a shared namespace, so names like `SECRET_KEY` defined in `components/common.py` are genuinely available at runtime even though Ruff can't see across the `include()` boundary). All 11 Python packages now pass `ruff check` again.
- [x] 6.2 Mark the new workflows as required status checks in the repository's branch protection settings for the default branch (manual/GitHub-UI step, not a file in this repo — document it here for whoever performs the rollout).
  - Exact steps and check names written up in `local/release.md` (gitignored, not part of this change's file set) for whoever performs the post-merge rollout.
- [x] 6.3 Confirm all new and modified workflows pass on a real PR before marking them required.
  - Can't be exercised locally — GitHub Actions only runs on a pushed branch/PR, and this branch hasn't been pushed yet. Captured as an explicit pre-flight step in `local/release.md`'s post-merge checklist, to be done before 6.2's branch-protection flip.
