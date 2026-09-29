## Why

`examples/authentication/custom-credentials` cannot be deleted today without breaking things well outside `examples/`: `core/backend`'s `poetry.lock`, both backend Dockerfiles (including the one that actually ships to the public Render demo), a required composer test suite, a silently-emptied import-boundary test, and the docs-site build all reach directly into that directory. Some of this is dead weight — `deploy/render/Dockerfile` copies the fixture plugin into the demo image even though it is never installed or loaded there. An example is supposed to be a disposable, illustrative artifact; right now it is a load-bearing dependency of the core codebase's build and required CI, which makes it unsafe to change or remove and hides real coverage gaps (a parametrized test that silently drops to zero cases if the directory goes away).

## What Changes

- Remove `atlas-example-auth-fixture` as a `core/backend` Poetry dependency entirely (not relocate it to another group) and regenerate `poetry.lock`.
- Remove the unconditional `COPY examples/authentication/custom-credentials/plugin ...` line from both `core/backend/Dockerfile` and `deploy/render/Dockerfile`; neither backend image will reference `examples/` again.
- Remove the example-plugin parametrization (`_example_authentication_package_dirs`, `test_example_authentication_plugins_use_only_public_sdk_imports`) from `core/backend/server/apps/plugins/tests/test_import_boundaries.py`; this check is already fully duplicated by `examples/authentication/validate.py`'s `imports` command.
- Move the assertions in `composer/atlas_composer/tests/test_authentication_examples.py` and `test_authentication_examples_ci.py` into `examples/authentication/validate.py` (or an equivalent self-contained check under `examples/authentication/`), after diffing them against `validate.py`'s existing `schemas`/`docs` commands to avoid duplicating coverage that already exists there. **BREAKING** (for anyone relying on these composer test IDs/paths): the composer pytest suite no longer validates example content; `examples/authentication/`'s own CI does.
- Remove the example-fixture-specific entries from `docs-site/scripts/validate_docs.py`'s `PROVIDER_SOURCES`/`PROVIDER_CONFIG_SOURCES`, and add an equivalent doc-accuracy check to `examples/authentication/validate.py`, invoked from `authentication-examples-fast.yml` instead of the general `pages.yml` docs build.
- Update `.github/workflows/authentication-examples-fast.yml` / `authentication-examples-integration.yml` step wiring as needed for the above moves; these workflows keep referencing `examples/` intentionally (they are the example's own CI and are expected to be deleted alongside it).
- Verify the end state by simulating deletion (e.g. removing `examples/authentication/custom-credentials` in an isolated worktree) and confirming no build, dependency-install, or required-test-suite coverage outside the example's own workflows fails. `pages.yml`'s generic doc-link checker is expected to also flag broken cross-reference links into the deleted directory — a doc-content concern, not a build/dependency coupling, and out of scope here.

Out of scope: the same reverse-dependency pattern for `examples/first-plugin/first-plugin-backend` in `docs-site/scripts/validate_docs.py`, and any other `examples/` subtree besides `examples/authentication/custom-credentials`. Flagged in design.md as a likely follow-up, not folded into this change.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `authentication-examples`: adds a requirement that examples are self-validating and safely deletable — no requirement outside `examples/authentication/` or its own dedicated CI workflows may depend on example content, so deleting an example only breaks that example's own workflows.
- `containerized-runtime`: adds a requirement that backend images (development and production, including the Render demo image) contain no example/fixture-only source that isn't part of their own installed dependency groups.

## Impact

- **Code**: `core/backend/pyproject.toml`, `core/backend/poetry.lock`, `core/backend/Dockerfile`, `deploy/render/Dockerfile`, `core/backend/server/apps/plugins/tests/test_import_boundaries.py`, `composer/atlas_composer/tests/test_authentication_examples.py`, `composer/atlas_composer/tests/test_authentication_examples_ci.py`, `examples/authentication/validate.py`, `docs-site/scripts/validate_docs.py`.
- **CI**: `.github/workflows/backend-tests.yml` (fewer fanned-out assertions), `.github/workflows/pages.yml` (drops example-path dependency), `.github/workflows/authentication-examples-fast.yml` (gains the ported checks).
- **Dependencies**: `core/backend`'s Poetry environment no longer has a path dependency on `examples/`; its lock file changes accordingly.
- **Build artifacts**: both backend Docker images shrink slightly and no longer contain the fixture plugin's source.
