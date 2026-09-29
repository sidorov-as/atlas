## Why

`catalog-info.yaml` manifests grow unwieldy as a repository accumulates more entities and concerns (System, Components, Resources, APIs, relationships) in one file, and today there is no way to split that content into separate fragments without either cramming everything into one multi-document file or scattering independent `catalog-info.yaml` files across directories (which only decomposes along directory boundaries, not by concern). Separately, ingestion is almost entirely silent on failure today: fetch failures, YAML parse failures, and manifest schema-validation failures only reach `logger.warning`/`logger.exception` — invisible outside application logs. Only claim-arbitration rejections (`ConflictRecord`) are persisted and visible in Django admin. Adding a new failure surface (unresolved `Include` paths) on top of that gap would make the inconsistency worse rather than better, so this change closes both at once.

## What Changes

- Add a new `kind: Include` manifest document, recognized within an already-discovered `catalog-info.yaml` (or within any fragment it includes), that composes in additional YAML fragments via `spec.paths` (explicit paths and/or globs), resolved relative to the including file's own directory.
- `Include` documents may be interleaved with ordinary entity documents in the same multi-document file, and are expanded before schema validation so they are never mistaken for an invalid entity document.
- Included fragments may themselves contain `kind: Include` documents (recursive composition), with cycle detection against the current resolution chain.
- Manifest discovery itself is unchanged: the connector continues to walk `**/catalog-info.yaml` across the whole repository tree (no move to a single root-manifest model) — `Include` is local composition within one discovered manifest, not a repository-wide ownership/index tree.
- An included fragment's filename MUST NOT be `catalog-info.yaml` (it would otherwise be ingested twice: once via tree-walk discovery, once via the `Include`); this is validated and reported rather than only documented.
- Add a new `IngestionIssue` model: a generalized, admin-visible, self-clearing record of ingestion-time problems that are not entity-claim conflicts — keyed by `(repository, path)`, storing the same human-readable message that already goes to the log, with `is_active`/`first_seen`/`last_seen` lifecycle (mirroring `ConflictRecord`'s existing dedup pattern, but as a separate model — `ConflictRecord` keeps its own settled, ref-keyed shape unchanged).
- Route the following existing silent failure paths through `IngestionIssue`, in addition to the new `Include`-specific failures (unresolved include path/glob, include fetch failure, include cycle detected, illegally-named included fragment): per-path fetch failure, per-path YAML parse failure, per-document manifest schema-validation failure.
- Register `IngestionIssue` in Django admin, mirroring `ConflictRecordAdmin`.

**Out of scope / explicitly deferred:**
- Database-schema (`DatabaseSchema` facet) ingestion — a separate, independent change, to be proposed later.
- Extending `ConflictRecord` with new `reason` values for the two *ref-identified* failure sites (duplicate ref within a repo, unresolved reference) — these fit `ConflictRecord`'s existing ref-keyed shape better than `IngestionIssue`'s path-keyed shape, but are left as plain logging in this change; a natural, explicitly-noted follow-up.
- A pre-commit validator tool for repo owners to catch the "fragment named `catalog-info.yaml`" mistake before it reaches ingestion — left as future work.
- Visibility into whole-repository-pass failures and connector/configuration errors (e.g. "no connector registered for source_id") — an operations/configuration concern with a different audience than manifest-authoring problems.

## Capabilities

### New Capabilities
- `ingestion-manifest-includes`: The `kind: Include` document — recognition, path resolution (relative to the including file, glob support), recursive expansion with cycle detection, the `catalog-info.yaml`-naming constraint on included fragments, and failure isolation for unresolved/failed includes.

### Modified Capabilities
- `catalog-ingestion`: Extends the existing "Per-manifest failure isolation" requirement — failures that are already isolated (per-repository, per-manifest-path, per-document) also become persisted and admin-visible via `IngestionIssue`, instead of only reaching the application log.

## Impact

- **Code**: `plugins/ingestion/backend/atlas_plugin_ingestion/pipeline.py` (new expansion step between raw parsing and duplicate-ref detection/validation; `IngestionIssue` writes at each existing and new failure site), `parsing.py` (or a new module) for `Include` document recognition, `models.py` (new `IngestionIssue` model + migration), `admin.py` (new `IngestionIssueAdmin`). No change to `connectors/base.py`'s `SourceConnector` interface — `fetch_file` already supports fetching an arbitrary repo-relative path.
- **Specs**: New `specs/ingestion-manifest-includes/spec.md`; a delta spec for `catalog-ingestion`. `ingestion-plugin`'s existing "All entity changes flow through the core Entity Service" requirement is unaffected — `Include` expansion happens before any `EntityIntent` is constructed, so no ingestion write path changes.
- **Data**: One new Django migration on the `atlas.ingestion` plugin's app (adds `IngestionIssue`; `ConflictRecord` and `RegisteredRepository` are unchanged).
- **Operators**: A new list in Django admin (`IngestionIssue`) to review alongside the existing `ConflictRecord` list.
