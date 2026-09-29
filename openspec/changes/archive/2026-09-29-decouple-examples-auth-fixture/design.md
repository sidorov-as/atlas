## Context

`examples/authentication/custom-credentials` is documentation made runnable: a fixture auth plugin (`atlas_example_auth_fixture`) plus a Compose topology, meant to demonstrate the public `atlas_plugin_api` credential-provider contract to third-party plugin authors. It was wired into the core codebase the same way a *real* plugin is (a Poetry path dependency, a Dockerfile `COPY`, a pytest fanout target) because that was the path of least resistance at the time: `core/backend/pyproject.toml` already had that pattern for every real plugin, and the composer test suite needed *some* venv to import the fixture from for its own regression tests.

The result, confirmed by tracing every reference into `examples/authentication/custom-credentials`:

- `core/backend/pyproject.toml`'s `dev` dependency group lists `atlas-example-auth-fixture` as a path dependency alongside real tooling (pytest, ruff, mypy). Poetry resolves path dependencies eagerly, so the directory must exist on disk for `poetry install` to succeed at all in that group.
- `core/backend/Dockerfile` and `deploy/render/Dockerfile` each `COPY` the fixture's source into a stage shared by both `development` and `production`/the demo image, purely so that `poetry install` step doesn't fail. Checked against `deploy/render/selected_plugins.py`: the fixture is not in `SELECTED_PLUGINS` for the demo, so in that image the copied source is never installed (main-only install skips the `dev` group) and never loaded by Django — pure dead weight, in the one Dockerfile that is an actual production deploy target.
- `composer/atlas_composer/tests/test_authentication_examples.py` and `test_authentication_examples_ci.py` read `examples/authentication/**` files directly and run as part of the root `pytest.ini` fanout, i.e. on every PR via `backend-tests.yml`.
- `core/backend/server/apps/plugins/tests/test_import_boundaries.py` globs the fixture's package directory to parametrize an import-boundary test. Confirmed this is a byte-for-byte duplicate of `validate_import_boundaries()` already in `examples/authentication/validate.py`, which already runs in `authentication-examples-fast.yml` — a workflow already correctly path-filtered to re-run on changes to `composer/`, `plugin-api/python/`, `plugins/auth-*/`, and `docs-site/**`, not just to `examples/`.
- `docs-site/scripts/validate_docs.py` hardcodes the fixture's `plugin.py`/`config.py` paths in `PROVIDER_SOURCES`/`PROVIDER_CONFIG_SOURCES` to check that documentation accurately names real fields/classes, and runs unconditionally in `pages.yml` (the general docs-site build, not scoped to example changes).

None of this was a deliberate decision that "core depends on examples"; it is what happens when a demo is bootstrapped using the same plumbing as a real plugin, and nobody later asked whether it should be safely deletable.

## Goals / Non-Goals

**Goals:**
- After this change, deleting `examples/authentication/custom-credentials` breaks no build, dependency-install, or required-test-suite coverage outside `examples/authentication/`'s own dedicated workflows (`authentication-examples-fast.yml`, `authentication-examples-integration.yml`) — verified by actually simulating the deletion, not just by inspection. This does not cover prose cross-reference links from other docs pages (e.g. `docs/operating-atlas/authentication.md`) to the example; those are expected to need updating as part of an actual deletion, same as any other doc removal, and `pages.yml`'s generic link checker will correctly flag them as broken until then.
- Preserve every check's *coverage*, just relocate it: import-boundary enforcement, manifest/lock schema validation, CI-workflow-shape assertions, and doc-accuracy checks against the fixture's real source all keep running, on the same triggers (including "changes to composer/plugin-api/plugins/docs-site" — not only "changes to examples/" — since those are exactly the changes that could desync the example from what it's supposed to demonstrate).
- Backend images (`core/backend/Dockerfile` `development`/`production`, and `deploy/render/Dockerfile`) contain no example/fixture source that isn't part of their own installed dependency groups.

**Non-Goals:**
- Fixing the same pattern for `examples/first-plugin/first-plugin-backend` (also hardcoded in `docs-site/scripts/validate_docs.py`) or any other `examples/` subtree. Flagged as a likely follow-up in Risks below.
- Changing what the example demonstrates or its Compose topology/README content.
- Restructuring `core/backend/Dockerfile`'s stage layout beyond removing the one `COPY` line and its knock-on `poetry install` flag — not splitting `base` into per-stage dependency-install stages (a heavier refactor, not required once the path dependency itself is gone).

## Decisions

### Remove the Poetry dependency entirely, not relocate it to a new group
Considered giving the fixture its own Poetry dependency group (e.g. `group.examples`) and having Docker install `--without examples`. Rejected: it still leaves `core/backend/pyproject.toml` naming a path inside `examples/`, which is exactly the coupling being removed. Once the composer tests that needed the fixture importable from `core/backend`'s venv move to `examples/authentication/`'s own tooling, `core/backend` has no remaining reason to know the path exists. Full removal is also strictly simpler: no new group, no `poetry install` flag changes for the `development` stage, no lock-file group bookkeeping — just delete the line and run `poetry lock`.

### Invert the validation direction: examples validate themselves against upstream contracts
Today, `core`'s and `composer`'s *required* test suites reach into `examples/` to check it hasn't drifted. That means `examples/` is validated by code that runs whether or not `examples/` changed, and disappears silently (the `test_import_boundaries.py` parametrize-on-empty-glob case) if `examples/` disappears.

The target shape, already half-built: `examples/authentication/validate.py` is a self-contained script that checks the example against the things it must stay compatible with (the public `atlas_plugin_api` import boundary, manifest/lock schemas, documented commands, secret hygiene, Compose rendering), run by `authentication-examples-fast.yml`, which is path-filtered to trigger on changes to the *upstream* surfaces the example depends on (`composer/`, `plugin-api/python/`, `plugins/auth-*/`, `docs-site/**`) as well as to itself. This is the correct direction: the dependent (`examples/`) checks itself against its dependencies (the SDK, composer's schemas, the docs), rather than the dependencies' test suites reaching forward into every consumer they don't otherwise need to know about.

Concretely this change:
- Deletes the duplicate check in `test_import_boundaries.py` (coverage already exists in `validate.py`).
- Ports the composer test suite's assertions into `validate.py` (or a sibling script/test module under `examples/authentication/`) after diffing against what `schemas`/`docs` already cover, so nothing is silently dropped.
- Ports `docs-site/scripts/validate_docs.py`'s fixture-specific doc-accuracy checks into the same place, called from `authentication-examples-fast.yml` (which already runs docs-site validation steps in the same job) instead of from `pages.yml`.

### Keep `pages.yml` docs-accuracy checking for non-example sources, drop it for the fixture only
`validate_docs.py`'s `PROVIDER_SOURCES` also lists `auth-oidc` and `auth-gitea` — real first-party plugins, not examples. Those entries stay in `docs-site/scripts/validate_docs.py` and keep running in `pages.yml` unconditionally, since `core`/`plugins/` genuinely are things the docs site is allowed to depend on describing accurately at every build. Only the fixture's entry moves.

## Risks / Trade-offs

- **[Risk]** Porting composer's test assertions into `examples/authentication/validate.py` could silently drop a check that has no equivalent yet in `validate.py`'s `schemas`/`docs` commands. → **Mitigation**: tasks.md sequences an explicit line-by-line diff of the composer test files against `validate.py` before deleting anything, and the final task re-verifies coverage by deleting the composer test files and confirming `authentication-examples-fast.yml` still catches an intentionally-broken example (or an equivalent dry-run check).
- **[Risk]** Moving doc-accuracy checks out of `pages.yml` means the docs site could build successfully with stale field/class names for the fixture between merges, only caught when `authentication-examples-fast.yml` next runs. → **Mitigation**: that workflow already runs on every PR that touches `docs-site/**`, `composer/`, or the example itself (per its existing path filters), so the gap is "runs in a different required job" rather than "runs less often."
- **[Risk]** `deploy/render/Dockerfile` is a live deploy path (`render-demo-reset.yml` rebuilds it nightly); removing its `COPY` line and `poetry install` behavior needs a real build verification, not just a diff read. → **Mitigation**: tasks.md includes actually building both Dockerfiles' targets, not just linting them.
- **[Trade-off]** `examples/first-plugin/first-plugin-backend`'s identical pattern in `validate_docs.py` is left in place. Anyone deleting that example hits the same problem this change just fixed for `custom-credentials`. Explicitly deferred rather than scope-creeped in; worth its own follow-up change once this one lands and the pattern is proven out.
- **[Risk, found during implementation]** `validate_docs.py`'s *generic* markdown/GitHub-URL link checker (distinct from the `PROVIDER_SOURCES`/`PROVIDER_CONFIG_SOURCES` checks this change ports out) still fails `pages.yml` if `custom-credentials` is actually deleted, because `docs/operating-atlas/authentication.md`, `docs/plugin-development/authentication-provider-sdk.md`, and the example's own `README.md` all link directly into it. Verified by simulating the deletion in an isolated worktree. → **Not fixed here**: this is prose cross-reference upkeep, the same obligation as removing any other linked doc, not the build/dependency coupling this change targets. The `authentication-examples` spec's deletion scenario was reworded to scope the guarantee accordingly (dependency install, Docker images, pytest — not docs-site's generic link check).

## Migration Plan

1. Diff composer's example-specific tests against `examples/authentication/validate.py`'s existing commands to find true gaps (no code change yet).
2. Extend `validate.py` (and/or add a sibling test module under `examples/authentication/`) to cover any gap found, plus the ported doc-accuracy checks.
3. Update `authentication-examples-fast.yml` to run the extended/new checks.
4. Delete `composer/atlas_composer/tests/test_authentication_examples.py`, `test_authentication_examples_ci.py`, and the example parametrization in `test_import_boundaries.py`.
5. Remove the Poetry path dependency, regenerate `poetry.lock`, remove the `COPY` lines from both Dockerfiles, adjust `poetry install` flags if needed, and rebuild both images to confirm they still build and run.
6. Remove the fixture-specific entries from `docs-site/scripts/validate_docs.py` and confirm `pages.yml` still passes.
7. Simulate deletion (remove `examples/authentication/custom-credentials` in an isolated worktree, not the real tree) and confirm: `poetry install`, both `docker build`s, and `pytest` from repo root all succeed. `pages.yml`'s generic link checker is expected to fail on cross-reference links into the deleted directory (a doc-content concern, not a build/dependency coupling) alongside `authentication-examples-fast.yml`/`authentication-examples-integration.yml`.

No runtime data migration or rollback strategy is needed — this is a build/CI/test topology change with no production data or API surface affected. Rollback is a plain revert.

## Open Questions

- Should the ported composer-test assertions live inside `examples/authentication/validate.py` itself (extending existing subcommands) or as a new `pytest`-based suite under `examples/authentication/tests/` run by the same workflow? Left for the implementer to decide during the gap-diff task, based on which assertions turn out to need pytest fixtures/parametrization versus a flat script check.
