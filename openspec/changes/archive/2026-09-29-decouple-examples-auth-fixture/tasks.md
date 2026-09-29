## 1. Gap analysis

- [x] 1.1 Diff `composer/atlas_composer/tests/test_authentication_examples.py` assertion-by-assertion against `examples/authentication/validate.py`'s `schemas`/`docs` commands; list every assertion with no equivalent yet.
- [x] 1.2 Diff `composer/atlas_composer/tests/test_authentication_examples_ci.py` against `validate.py` and `authentication-examples-integration.yml` the same way; list every assertion with no equivalent yet.
- [x] 1.3 Confirm `core/backend/server/apps/plugins/tests/test_import_boundaries.py`'s `test_example_authentication_plugins_use_only_public_sdk_imports` has no assertion beyond what `validate.py`'s `validate_import_boundaries()` already checks (expected: none, per prior investigation — re-verify before deleting).
- [x] 1.4 List every entry in `docs-site/scripts/validate_docs.py`'s `PROVIDER_SOURCES`/`PROVIDER_CONFIG_SOURCES` that points into `examples/authentication/custom-credentials`, and what each one actually asserts about the docs.

## 2. Port coverage into `examples/authentication/`

- [x] 2.1 Extend `examples/authentication/validate.py` (or add a sibling test module under `examples/authentication/`) to cover every gap found in 1.1 and 1.2.
- [x] 2.2 Add a doc-accuracy check to `examples/authentication/validate.py` covering every entry found in 1.4 (same kind of check `docs-site/scripts/validate_docs.py` does today, scoped to the fixture's source).
- [x] 2.3 Update `.github/workflows/authentication-examples-fast.yml` to run the new/extended checks from 2.1 and 2.2, keeping its existing path filters (or extending them if the ported checks need triggers the workflow doesn't already have).
- [x] 2.4 Run the updated `validate.py`/workflow locally or via `workflow_dispatch` and confirm the new checks pass against the current (unmodified) example.

## 3. Remove the now-redundant checks

- [x] 3.1 Delete `composer/atlas_composer/tests/test_authentication_examples.py` and `test_authentication_examples_ci.py` (the one non-example assertion, `test_official_distribution_keeps_explicit_conservative_local_auth`, was already extracted to `composer/atlas_composer/tests/test_default_distribution.py` during 2.1, since it tests `distributions/default`, not an example).
- [x] 3.2 Remove `_example_authentication_package_dirs` and `test_example_authentication_plugins_use_only_public_sdk_imports` from `core/backend/server/apps/plugins/tests/test_import_boundaries.py`, and any now-unused helpers/imports left behind.
- [x] 3.3 Remove the fixture-specific entries from `docs-site/scripts/validate_docs.py`'s `PROVIDER_SOURCES`/`PROVIDER_CONFIG_SOURCES` (leave the `auth-oidc`/`auth-gitea` entries in place).
- [x] 3.4 Run `pytest` from the repo root and confirm the full suite still passes with these files gone.
- [x] 3.5 Run `docs-site`'s `validate_docs.py` (and its own `test_validate_docs.py`) and confirm it still passes without the fixture entries.

## 4. Remove the Docker/Poetry coupling

- [x] 4.1 Remove the `atlas-example-auth-fixture` path dependency from `core/backend/pyproject.toml`'s `dev` group.
- [x] 4.2 Regenerate `core/backend/poetry.lock` and confirm `poetry install` succeeds from a clean state without `examples/` present in the resolution.
- [x] 4.3 Remove the `COPY examples/authentication/custom-credentials/plugin ...` line from `core/backend/Dockerfile`.
- [x] 4.4 Remove the equivalent `COPY` line from `deploy/render/Dockerfile`.
- [x] 4.5 Build the `development` and `production` targets of `core/backend/Dockerfile` and confirm both succeed and contain no `examples/` path.
- [x] 4.6 Build `deploy/render/Dockerfile` and confirm it succeeds and contains no `examples/` path.
- [x] 4.7 Bring up `docker-compose.dev.yml` and confirm the backend starts and `manage.py` commands run normally.

## 5. Verify full decoupling

- [x] 5.1 Remove `examples/authentication/custom-credentials` from the tree to simulate deletion (done via an isolated `git worktree` off a `git stash create` snapshot of the in-progress branch — leaves the real working tree untouched and is cleanly discardable; `git rm -r` inside that worktree).
- [x] 5.2 With it removed, confirm: `poetry install` in `core/backend` (✅), both Docker builds (4.5/4.6) (✅ both `core/backend/Dockerfile` targets and `deploy/render/Dockerfile`), `pytest` from the repo root (✅ 1370 passed). `docs-site/scripts/validate_docs.py` **fails as expected** — its generic link checker flags cross-reference links in `docs/operating-atlas/authentication.md`, `docs/plugin-development/authentication-provider-sdk.md`, and the example's own `README.md`. This is a doc-content concern (found during this task), not the build/dependency coupling this change targets; `proposal.md`/`design.md`/the `authentication-examples` spec scenario were reworded accordingly to scope the guarantee to dependency install + Docker images + pytest.
- [x] 5.3 Read every workflow's `on.push`/`on.pull_request` trigger (no `workflow_dispatch` runs needed for a read-only path-filter check):
  - `authentication-examples-fast.yml`, `authentication-examples-integration.yml`: path-filtered to `examples/authentication/**` — the only workflows expected to fail on a deletion commit (their own CI, by design).
  - `backend-tests.yml`, `dependency-audit.yml` (its `pip-audit` job): no path filter, so they run on every push/PR — both run `poetry install` from `core/backend`, which now succeeds without the fixture (verified in 4.2/5.2), so both **pass** where they would previously have failed hard on the missing path dependency.
  - `frontend-checks.yml`, `ruff.yml`, `secret-scan.yml`: no path filter, run on every push/PR, but contain no reference to `examples/` at all — unaffected either way.
  - `migration-lint.yml`: path-filtered to `**/migrations/**`; wouldn't trigger on this deletion.
  - `pages.yml`: path-filtered to `docs-site/**` only — would **not even trigger** on a commit that only deletes `examples/authentication/custom-credentials`. Its generic link-check failure (5.2) is latent: it only surfaces the next time `docs-site/**` changes and `pages.yml` runs against a tree where the example is already gone. Documented as a known consequence in design.md, not a new build coupling.
  - `render-demo-reset.yml`: schedule/`workflow_dispatch` only, not push/PR-triggered; its Dockerfile build already verified to succeed without the fixture (4.6/5.2).
- [x] 5.4 Discarded the isolated worktree (`git worktree remove --force`); the real working tree was never modified, so nothing to restore there.

## 6. Documentation

- [x] 6.1 Update any contributor-facing docs that describe the composer test suite's scope or `core/backend`'s dev dependencies, if they mention the fixture. Searched repo-wide (`CONTRIBUTING.md`, `README.md`, `docs-site/docs/**`) for mentions of `atlas-example-auth-fixture`/`atlas_example_auth_fixture`/the deleted composer test modules/dev-dependency or pytest-fanout language: none found outside the example's own `README.md` (which correctly still names its own package) and the doc-site cross-reference links already covered by 5.2/design.md. No changes needed.
- [x] 6.2 Note in this change's PR description that `examples/first-plugin/first-plugin-backend`'s identical pattern in `docs-site/scripts/validate_docs.py` is a known, deliberately out-of-scope follow-up. No PR exists yet (`gh` isn't authenticated in this environment), so the note is drafted below for the PR description when one is opened:

  > **Known follow-up (out of scope here):** `examples/first-plugin/first-plugin-backend` has the same hardcoded-path pattern in `docs-site/scripts/validate_docs.py`'s `PROVIDER_SOURCES`/`PROVIDER_CONFIG_SOURCES` that this change just fixed for `examples/authentication/custom-credentials`. Deliberately left in place — worth its own follow-up change once this pattern is proven out (see design.md's Risks/Trade-offs).
  >
  > Also found during implementation (5.2/5.3): `docs-site/scripts/validate_docs.py`'s *generic* link checker (distinct from the ported field/class-accuracy checks) will still fail `pages.yml` if `examples/authentication/custom-credentials` is ever actually deleted, because `docs/operating-atlas/authentication.md`, `docs/plugin-development/authentication-provider-sdk.md`, and the example's own `README.md` link directly into it. That's prose cross-reference upkeep, not a build/dependency coupling, and is scoped out of the `authentication-examples` spec's deletion guarantee accordingly.
