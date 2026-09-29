## 1. Shared path-validation helper

- [x] 1.1 Add a repository-relative path-validation helper in `plugins/ingestion/backend/atlas_plugin_ingestion/` (e.g. `paths.py`): given a base directory, an entry, and a checkout root, reject absolute paths, `..` segments, and NUL/control characters, and verify the resolved path's `is_relative_to()` the resolved checkout root.
- [x] 1.2 Unit test the helper directly: valid relative path, absolute path, `..` traversal, NUL byte, control character, symlink escaping the checkout.

## 2. Wire validation into Include and sourceSqlPath resolution

- [x] 2.1 Wire the helper into `pipeline.py`'s `_resolve_include_entry`; on rejection, record an `IngestionIssue` and treat the entry as a failed resolution (existing failure-isolation pattern).
- [x] 2.2 Wire the helper into `database_schema.py`'s `_resolve_source_sql_path`; same rejection/reporting pattern.
- [x] 2.3 Add tests: `Include.spec.paths` with `/etc/passwd` and `../../etc/passwd`, each rejected without blocking the rest of the manifest. (Symlink-escape coverage moved to 3.2: `pipeline.py`/`database_schema.py` validate repository-relative path *strings* before any real checkout exists — there is no filesystem to resolve a symlink against yet, only at the connector's real checkout, task 3. See `paths.py`'s module docstring and this decision confirmed with the user during implementation.)
- [x] 2.4 Add tests: `sourceSqlPath` with `/etc/passwd` and `../../etc/passwd`, each rejected without blocking the Resource's own entity upsert. (Symlink-escape coverage moved to 3.2, same reason as 2.3.)

## 3. Enforce containment at the connector read boundary

- [x] 3.1 Re-verify path containment inside `GitCheckout.read` (or `GitConnector.fetch_file`) itself, independent of the pre-checks in tasks 2.1/2.2, so a future caller cannot bypass validation by skipping the pre-check.
- [x] 3.2 Add a test that calls `fetch_file`/`read` directly with an absolute/traversal path (bypassing `pipeline.py`/`database_schema.py`) and confirms it still fails; include a symlink-escape case here (moved from 2.3/2.4 — this is the first point with a real checkout to resolve one against).

## 4. Resource limits

- [x] 4.1 Add a configured maximum fetched-file size, enforced before YAML parsing, applied to manifest discovery, `Include` fragment fetches, and `sourceSqlPath` fetches.
- [x] 4.2 Add a configured maximum YAML document size/nesting depth, enforced during parsing.
- [x] 4.3 Add a configured maximum `Include` recursion depth in `pipeline.py`'s expansion loop, alongside the existing cycle-detection `visited` tracking.
- [x] 4.4 Add a configured maximum total included-file count per ingestion run.
- [x] 4.5 Tests: oversized file rejected before parsing, excessively nested YAML rejected, Include depth limit rejected without a cycle present, total-included-file-count limit rejected.

## 5. Non-root container user

- [x] 5.1 Add a non-root `USER` (with appropriate working-directory ownership) to `core/backend/Dockerfile`, applied to both `development` and `production` stages.
- [x] 5.2 Verify the documented development Compose (bind-mount) workflow still starts and reads/writes the mounted source successfully under the non-root user.
- [x] 5.3 Verify the documented production Compose workflow still builds, migrates, and starts successfully under the non-root user.

## 6. Verification

- [x] 6.1 Run the full `atlas_plugin_ingestion` and `atlas_plugin_database_schema` test suites.
- [x] 6.2 Confirm `openspec validate fix-ingestion-path-traversal` passes.
- [x] 6.3 Manually verify against a test repository containing an absolute-path `Include` and an absolute-path `sourceSqlPath` that both are rejected end-to-end (not just at the unit level).
