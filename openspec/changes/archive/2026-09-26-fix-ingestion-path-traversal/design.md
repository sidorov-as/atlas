## Context

Ingestion resolves two independent path-shaped inputs against a repository checkout: `kind: Include`'s `spec.paths` (`pipeline.py:_resolve_include_entry`, relative to the declaring file's directory) and `spec.databaseSchema.sourceSqlPath` (`database_schema.py:_resolve_source_sql_path`, also relative to the declaring file's directory, but resolved independently by an existing design decision — see `database_schema.py`'s own docstring reference to "design.md D1"). Both eventually call `connector.fetch_file(repo, resolved_path, sha)`, which for `GitConnector` reaches `GitCheckout.read(path)`:

```python
def read(self, path: str) -> bytes:
    return (Path(self.directory) / PurePosixPath(path)).read_bytes()
```

`pathlib`'s `/` operator discards the left operand entirely when the right operand is an absolute `PurePosixPath` — `Path("/checkout") / PurePosixPath("/etc/passwd")` evaluates to `PurePosixPath("/etc/passwd")`. Neither `_resolve_include_entry` nor `_resolve_source_sql_path` rejects an absolute `entry`/`source_sql_path`, and `PurePosixPath(base_dir, entry)` itself also collapses to `entry` when `entry` is absolute (the same discarding behavior, one level up). `..` segments are likewise never rejected, so a resolved-but-relative-looking path can still walk outside the checkout. The backend/ingestion container also runs as root (no `USER` in `core/backend/Dockerfile`), so a successful escape reads with root's file access inside the container.

`catalog-ingestion`'s Registered Repository `path` field already has exactly this validation discipline ("rejects empty, leading `/`, `..` segment, control/whitespace characters, `://`") — this change is bringing `Include.spec.paths` and `sourceSqlPath` up to the same bar, not inventing a new one.

## Goals / Non-Goals

**Goals:**
- Any resolved path used to read repository content is provably contained within the repository checkout before the read happens, enforced at the point of the read, not only at the point of resolution.
- The same validation primitive is reused by both `Include.spec.paths` and `sourceSqlPath`, so a future third path-shaped input doesn't need to reinvent it.
- Ingestion of a single manifest tree cannot consume unbounded memory or time via oversized files, deeply nested YAML, or unbounded `Include` fan-out.
- The backend/ingestion container runs as a non-root user.

**Non-Goals:**
- Merging `Include` path resolution and `sourceSqlPath` resolution into one code path — `database_schema.py` resolves independently of `pipeline.py` by an existing, deliberate design decision; this change shares only the validation *primitive*, not the resolution *flow*.
- Changing how ingestion credentials or `source_id`/`baseUrl` configuration work — out of scope, no evidence of a related issue there.
- General ingestion rate-limiting or scheduling changes — the resource limits here bound a single fetch/parse operation, not the ingestion scheduler.
- SSRF protections for ingestion's own outbound Git fetch — the connector fetches from an operator-configured, already-registered source; that trust boundary is different from the user-supplied `specUrl` case handled by the separate `fix-apis-ssrf`/`add-safe-http-helper` changes.

## Decisions

- **Enforce containment inside the connector's read path, not only at the callers.** A helper like `resolve_repository_relative(base_dir: PurePosixPath, entry: str, checkout_root: Path) -> Path | None` returns `None` (rejected) for absolute paths, `..` segments, NUL/control characters, or a resolved path that fails `is_relative_to(checkout_root.resolve())`. Both `pipeline.py` and `database_schema.py` call it before invoking `fetch_file`, AND `GitCheckout.read` independently re-verifies containment before opening the file — defense in depth, since a future caller of `fetch_file` that forgets the pre-check must not be able to escape. Chosen over "validate once at the call site and trust it downstream" because the audit's finding was specifically that the *only* check that existed was easy to bypass by adding a new caller.
- **Reject rather than sanitize.** An absolute path or `..`-containing entry is treated as a failed resolution (recorded as an `IngestionIssue`, same failure-isolation pattern already used for missing includes), not silently rewritten to something "safe." Silent rewriting could mask a manifest author's mistake and produce confusing ingested content.
- **Resource limits live at the fetch/parse boundary, not per-capability.** A single `MAX_FETCHED_FILE_BYTES` and YAML complexity ceiling applied wherever `fetch_file` content is parsed, rather than separate ad hoc limits duplicated in `pipeline.py` and `database_schema.py`. `Include` recursion depth and total-included-file-count limits are specific to `pipeline.py`'s own expansion loop (which already tracks a `visited` set for cycle detection) and are added there directly.
- **Non-root container user is a plain `USER` addition, not a rearchitecture.** `core/backend/Dockerfile` currently has no non-root user at all; add one (e.g. `appuser`) with ownership of the working directory, applied to both `development` and `production` stages, since the ingestion worker runs from the same image.

## Risks / Trade-offs

- **A previously-working manifest that happened to rely on an absolute or `..`-escaping path will start failing** → acceptable and intended: such a manifest was already relying on undefined/unsafe behavior; it will now surface as a reported `IngestionIssue` instead of silently reading unintended content. Call this out in the change's release notes.
- **Adding a non-root `USER` can break file permissions for bind-mounted development volumes** → mitigate by matching the container user's UID/GID to common host-user conventions or documenting a build-arg override, and verifying the documented development Compose workflow still works after the change (containerized-runtime spec's "Source-mounted development topology" requirement).
- **Resource limits could reject a legitimately large existing SQL file or manifest tree** → mitigate by setting initial limits generously (order of magnitude above realistic manifest/SQL sizes seen in the repo's own examples) and making them operator-configurable rather than hardcoded constants, so a real deployment isn't stuck if it legitimately needs more.
- **Symlink escape**: `is_relative_to` on a `.resolve()`d path already follows symlinks to their real target, so a symlink inside the checkout pointing outside it is caught by the same containment check — call this out explicitly in the negative-test suite (proposal's "Impact"/tasks) rather than assuming path containment alone covers it without a test.

## Migration Plan

1. Add the shared path-validation helper and its unit tests (absolute, `..`, NUL/control chars, symlink escape, valid relative path).
2. Wire it into `pipeline.py`'s `_resolve_include_entry` and `database_schema.py`'s `_resolve_source_sql_path`.
3. Wire containment re-verification into `GitCheckout.read` / `GitConnector.fetch_file`.
4. Add fetched-content and YAML-complexity size limits at the parse boundary.
5. Add `Include` recursion-depth and total-included-file-count limits in `pipeline.py`'s expansion loop.
6. Add the non-root `USER` to `core/backend/Dockerfile`; verify development bind-mount workflow and production build both still work.
7. Add negative tests for all of the above; run the full ingestion plugin test suite.

No data migration; no rollback complexity beyond reverting the change (no schema changes).

## Open Questions

- Exact numeric values for the new limits (max file size, max YAML nesting, max Include depth/fan-out, container UID) are left to implementation — should be informed by the largest legitimate examples already in the repo's own `plugins/ingestion/backend` test fixtures/examples.
