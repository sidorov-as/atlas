## 1. Baseline

- [x] 1.1 Run `ruff check` per package (`core/backend`, `plugin-api/python`, and each `plugins/*/backend`) and save the current violation list per package as a starting baseline for comparison.
- [x] 1.2 Run each package's existing test suite once before any change, to have a known-green (or known-baseline) reference point.

## 2. Safe auto-fixes

- [x] 2.1 Run `ruff check --fix` per package to resolve `I001` (unsorted-imports), `RUF100` (unused-noqa), `FURB188`, `RUF022`, and `TC005`.
- [x] 2.2 Run `ruff format` per package where applicable, to mechanically close as many `E501` gaps as it safely can.
- [x] 2.3 Diff-review the auto-fixed changes per package to confirm nothing beyond formatting/import order moved.

## 3. Manual E501 reflow

- [x] 3.1 core/backend: reflow remaining long lines. (263 lines across 29 files, done via three parallel background passes over disjoint file sets: `seed_booking_demo.py`+its test, the demo/service/model files, and the remaining test files. Verified value-preservation via AST/YAML/SQL round-trip comparisons where the content wasn't free-form prose; a handful of long `def test_...(` lines were shortened since identifiers can't be split, confirmed to have no other references first.)
- [x] 3.2 plugin-api/python: reflow remaining long lines. (E501 isn't in this package's own resolved Ruff config — no fallback `select` includes it — so there was never a violation here; confirmed zero after the auto-fix/format pass.)
- [x] 3.3 plugins/ingestion/backend: reflow remaining long lines. (same: E501 not selected under this package's own config; zero violations.)
- [x] 3.4 plugins/apis/backend: reflow remaining long lines. (same: E501 not selected; zero violations.)
- [x] 3.5 plugins/auth-oidc/backend: reflow remaining long lines. (explicit `select = [E, F, I, UP, W]` includes E501; zero violations after auto-fix/format.)
- [x] 3.6 plugins/auth-gitea/backend: reflow remaining long lines. (same explicit select; zero violations.)
- [x] 3.7 plugins/standard-catalog/backend: reflow remaining long lines. (E501 not selected under this package's own config; zero violations.)
- [x] 3.8 plugins/database-schema/backend: reflow remaining long lines. (same: not selected; zero violations.)
- [x] 3.9 plugins/c4/backend: reflow remaining long lines. (same: not selected; zero violations.)
- [x] 3.10 plugins/flows/backend: reflow remaining long lines. (same: not selected; zero violations.)
- [x] 3.11 Spot-check that no long line was reflowed inside a string literal (SQL, regex, URL) in a way that changed its value. (Verified per-file during 3.1: AST string-constant diffing, YAML round-trip parse equality for embedded specs, `sqlglot` round-trip equality for embedded DDL, and a coordinator-level spot-check of the diffs after all three passes landed. Full test suite stayed at 1265 passed throughout.)

## 4. RUF012 mutable-class-default fixes

- [x] 4.1 Enumerate every `RUF012` occurrence per package. (`core/backend`, `plugins/auth-oidc/backend`, `plugins/auth-gitea/backend` don't select `RUF` at all under their own declared config, so RUF012 doesn't apply there; the remaining 7 packages had 140 occurrences: 82 in auto-generated Django migration `Migration.dependencies`/`operations`, 58 in application code.)
- [x] 4.2 For each occurrence, check whether any code path relies on the mutable default being shared across instances (grep for mutation of the attribute, check tests). (Every occurrence was a read-only declarative constant — Django `Migration.dependencies`/`operations`, model `Meta.ordering`/`Meta.constraints`, `*_CHOICES` field-choice lists, kind-handler `provides` lists, admin `actions` — never mutated, never relied upon for cross-instance sharing.)
- [x] 4.3 Fix each occurrence to use a per-instance default (`dataclasses.field(default_factory=...)`, `None`-then-initialize in `__init__`, or equivalent for the class type in use). (None of these are dataclasses/`__init__`-built instances varying per call; the correct, Ruff-suggested fix for a genuinely shared declarative constant is `typing.ClassVar[...]` annotation, applied to all 140 occurrences.)
- [x] 4.4 If any occurrence turns out to rely on the shared state intentionally, flag it separately rather than silently changing behavior — do not fix it as part of this change. (None did — nothing to flag.)

## 5. Remaining manual-judgment rules

- [x] 5.1 Fix the `SIM117` occurrence (multiple-with-statements → merge into one `with`). (`plugins/ingestion/backend/atlas_plugin_ingestion/tests/test_git_connector_integration.py` — merged nested `with GitConnector(...)` / `with pytest.raises(...)` into one `with (...)`.)
- [x] 5.2 Fix the `PYI034` occurrence (non-self-return-type). (`plugins/ingestion/backend/atlas_plugin_ingestion/connectors/git.py` `GitConnector.__enter__` — changed `-> "GitConnector"` to `-> Self`.)
- [x] 5.3 Fix the `EXE002` occurrence (shebang-missing-executable-file — either add the executable bit or drop the shebang). (No `EXE002` violation exists in any package under its own declared config — verified with an explicit `--select EXE002` pass across all 10 packages; nothing to fix.)
- [x] 5.4 Fix the `PLW1510` occurrence (subprocess-run-without-check — decide and set `check=` explicitly). (`plugins/ingestion/backend/atlas_plugin_ingestion/tests/test_git_connector_integration.py` `_docker_available()` — added `check=False`, since the caller reads `probe.returncode` itself rather than wanting an exception.)
- [x] 5.5 Fix the `TRY004` occurrence (type-check-without-type-error). (`plugins/apis/backend/atlas_plugin_apis/asyncapi_import.py` — an `isinstance` check now raises `TypeError` instead of `ValueError`; the only caller catches bare `Exception`, so this doesn't change control flow.)

## 6. Verification

- [x] 6.1 Run `ruff check` per package and confirm zero violations against each package's own declared config. (All 10 packages report "All checks passed!".)
- [x] 6.2 Run each package's test suite and confirm no regressions versus the 1.2 baseline. (Full-repo run: 1265 passed, matching the 1.2 baseline exactly — this repo's single root `pytest.ini` runs every package's tests together for correct fixture scoping, see its header comment.)
- [x] 6.3 Run the full-repo Python test commands used elsewhere in CI (composer + plugin API tests) to catch any cross-package breakage. (Same root-level `pytest` run covers `composer`, `plugin-api/python`, and every plugin's tests together — 1265 passed, 0 failed.)
- [x] 6.4 Confirm no `pyproject.toml` Ruff configuration was loosened to make violations disappear. (`git diff` on every `pyproject.toml` in the repo is empty — no config file was touched.)
