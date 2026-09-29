## 1. `IngestionIssue` model

- [x] 1.1 Add `IngestionIssue` model to `plugins/ingestion/backend/atlas_plugin_ingestion/models.py` (`repository` FK nullable/`SET_NULL`, `repo_full_name`, `path` blank-allowed, `message`, `is_active`, `first_seen`, `last_seen`), mirroring `ConflictRecord`'s shape.
- [x] 1.2 Add `_record_issue(repo, path, message)` / `_resolve_issue(repo, path)` helpers (find-or-create by `(repository, path)`, refresh `message`/`last_seen`/`is_active=True` on recurrence; clear on success) — same pattern as `upsert.py`'s `_record_conflict`/`_resolve_conflicts`, placed wherever makes sense for `pipeline.py` to call (e.g. alongside the pipeline, not inside `upsert.py`, since these are pipeline-stage failures, not claim arbitration).
- [x] 1.3 Generate and apply the Django migration (next after `0004_registeredrepository_source_id_path.py`).
- [x] 1.4 Register `IngestionIssueAdmin` in `admin.py`, mirroring `ConflictRecordAdmin` (`list_display` with repo/path/message/is_active/first_seen/last_seen, `list_filter` on `is_active`, `search_fields` on path/message).

## 2. `kind: Include` recognition and local expansion

- [x] 2.1 Add Include-document recognition (a raw dict with `kind: Include` and `spec.paths`) as a distinct case in the document-processing flow, separate from entity documents, so it never reaches `validate_manifest_document`.
- [x] 2.2 Implement path resolution for `spec.paths` entries relative to the directory of the file that declared the `Include` (not repo root, not the top-level manifest when nested).
- [x] 2.3 Implement glob matching for `spec.paths` entries against the repository's known file listing (reuse/extend connector-provided file listing rather than requiring a new connector method, if feasible; otherwise define the minimal new connector capability needed).
- [x] 2.4 Reject (and route to `IngestionIssue`, see 3.x) any resolved include path whose basename is `catalog-info.yaml`.
- [x] 2.5 Fetch and parse each resolved path via the existing `SourceConnector.fetch_file`/`parsing.py` machinery, folding resulting raw documents into the same document pool as the including file.

## 3. Recursive expansion, cycle detection, and failure isolation

- [x] 3.1 Make Include expansion recursive: a fragment's own `kind: Include` documents are expanded the same way as 2.1–2.5.
- [x] 3.2 Track visited repository-relative paths through the current resolution chain; reject (not recurse on) a path revisit, routed to `IngestionIssue` with a clear cycle-description message.
- [x] 3.3 On an unresolved/empty glob, a fetch failure, or a rejected cycle/naming violation, skip only that `Include` path entry (and record an `IngestionIssue`), leaving the rest of the including document's own entities, the rest of that `Include` document's other paths, and the rest of the repository's manifests unaffected.

## 4. Route existing silent failures through `IngestionIssue`

- [x] 4.1 `pipeline.py`'s per-path connector fetch failure (`"Failed to fetch %s from %s"`) — also record an `IngestionIssue`.
- [x] 4.2 `pipeline.py`'s YAML parse failure (`"Failed to parse %s from %s"`) — also record an `IngestionIssue`.
- [x] 4.3 `pipeline.py`'s manifest schema-validation failure (`"Skipping invalid manifest document..."`) — also record an `IngestionIssue`.
- [x] 4.4 On a clean run for a given `(repository, path)` (no fetch/parse/validation/include failure for that path), clear any existing active `IngestionIssue` for it.

## 5. Tests

- [x] 5.1 Unit tests for Include recognition/expansion: single include, glob include, mixed Include + entity documents in one file, nested/recursive includes.
- [x] 5.2 Unit tests for cycle detection (direct and indirect cycles).
- [x] 5.3 Unit tests for the `catalog-info.yaml`-named-fragment rejection.
- [x] 5.4 Unit tests for `IngestionIssue` lifecycle: created on failure, `message`/`last_seen` updated on recurrence, `is_active` cleared on a subsequent clean run, no duplicate rows across repeated failing runs.
- [x] 5.5 Integration test: a repository with a top-level `catalog-info.yaml` including a `.manifests/` directory (via glob) ingests every entity from both the top-level file and its fragments in one run.
- [x] 5.6 Regression test: existing scattered-`catalog-info.yaml`-per-directory discovery and plain multi-document manifests (no `Include` involved) continue to behave exactly as before.

## 6. Documentation

- [x] 6.1 Document the `kind: Include` manifest shape, path-resolution rule, glob support, recursion, and the `catalog-info.yaml`-naming constraint (likely `docs-site/docs/features/ingestion.md` and/or `docs-site/docs/using-atlas/ingest-repository.md`).
- [x] 6.2 Document `IngestionIssue` in the operator-facing troubleshooting docs (`docs-site/docs/using-atlas/troubleshoot-ingestion.md`), alongside the existing `ConflictRecord` guidance.
