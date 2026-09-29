## Why

A prerelease security audit found that ingestion's two path-shaped inputs — `kind: Include`'s `spec.paths` and `spec.databaseSchema.sourceSqlPath` — resolve without rejecting absolute paths or `..` traversal, and the git connector's file read discards its checkout root entirely when given an absolute path (`Path(checkout_dir) / PurePosixPath(absolute_path)` evaluates to the absolute path, per pathlib semantics). A controlled Git repository connected for ingestion can therefore read arbitrary files reachable inside the backend container — `/etc/shadow`, mounted secrets, source code — and for `sourceSqlPath` specifically, the raw content is stored and returned to any authenticated user regardless of whether it is actually SQL. The container also runs as root (no `USER` in `core/backend/Dockerfile`), which widens the blast radius of any such read. This is a P0 release blocker: it must be fixed before Atlas can be published as safe to run.

Notably, `catalog-ingestion`'s existing "Registered Repository" requirement already validates the repository-registration `path` field against exactly this class of attack (rejects `..`, leading `/`, control characters) — this change closes the gap where that same discipline was never applied to `Include.spec.paths` or `sourceSqlPath`.

The related Medium-priority "unlimited ingestion" finding (unbounded file reads, unbounded YAML parsing, unbounded Include recursion/fan-out) touches the same code paths and is folded in here rather than revisited later.

## What Changes

- Add a shared, repository-relative path-validation function used by both `Include.spec.paths` resolution (`pipeline.py`) and `sourceSqlPath` resolution (`database_schema.py`): reject absolute paths, `..` segments, NUL bytes, and control characters. (`database_schema.py` intentionally resolves independently of `pipeline.py`'s Include resolution per an existing design decision — this shares only the validation primitive, not the resolution flow itself.)
- Enforce the check inside the connector's file-read path itself (`GitConnector.fetch_file` / the underlying checkout `read`), verifying `candidate.resolve().is_relative_to(checkout_root.resolve())`, so no current or future caller can bypass it by skipping an earlier check.
- Add resource limits to the ingestion pipeline: a maximum fetched-file size, a maximum YAML document size/nesting complexity, a maximum `Include` recursion depth, and a maximum total number of included files per run.
- Add a non-root `USER` to `core/backend/Dockerfile` for both the `development` and `production` stages (the ingestion worker runs from this same image).
- Add negative tests: absolute path (`/etc/passwd`), `../../` traversal, and symlink escape, covering both `Include.spec.paths` and `sourceSqlPath`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ingestion-manifest-includes`: "Include paths resolve relative to the including file's directory" gains an explicit requirement that resolved paths must stay within the repository checkout — absolute paths and `..` traversal are rejected rather than silently escaping — plus a bound on total recursion depth/fan-out (building on the existing cycle-detection requirement, which prevents infinite loops but not large-but-finite blowups).
- `ingestion-database-schema`: "A Resource manifest may declare its Database Schema source" gains the same path-containment requirement for `sourceSqlPath`, plus a maximum fetched-file size.
- `catalog-ingestion`: gains a requirement that fetched manifest/fragment content and its parsed YAML are subject to a size and complexity ceiling, enforced uniformly regardless of which capability triggered the fetch.
- `containerized-runtime`: gains a requirement that application containers (backend and ingestion worker) run as a non-root user in both development and production images.

## Impact

- `plugins/ingestion/backend/atlas_plugin_ingestion/pipeline.py` (Include path resolution)
- `plugins/ingestion/backend/atlas_plugin_ingestion/database_schema.py` (`sourceSqlPath` resolution)
- `plugins/ingestion/backend/atlas_plugin_ingestion/connectors/git.py` and `connectors/base.py` (path containment enforcement, resource limits)
- `plugins/database-schema/backend/atlas_plugin_database_schema/facet_writer.py` (receives the now-bounded fetched content; no interface change expected)
- `core/backend/Dockerfile` (non-root `USER`)
- No REST API surface changes; no breaking changes to manifest authoring for repositories that were already using relative, in-checkout paths (the only behavior change is that previously-silent-escape inputs now fail with a reported issue instead of succeeding).
