## Context

Ingestion (`atlas.ingestion` plugin, `plugins/ingestion/backend/atlas_plugin_ingestion/`) today works in two stages per registered repository (`pipeline.py`'s `_ingest_repository`):

1. **Discovery**: `GitConnector.list_manifest_paths()` (`connectors/git.py`'s `_Checkout.manifest_paths()`) walks the whole repository tree and returns every path literally named `catalog-info.yaml` (`connectors/base.py`'s `MANIFEST_FILENAME`).
2. **Parse + upsert**: each discovered file is fetched and split into raw documents on `---` (`parsing.py`'s `parse_manifest`, a flat list with no notion of "file"), collected into one flat pool for the whole repository, deduplicated by `(kind, namespace, name)` (`pipeline.py`'s `_drop_duplicate_refs`), then validated and upserted one at a time (`upsert.py`'s `upsert_entity`), followed by a second pass reconciling declared relationships and removing stale claims.

Failure handling today is asymmetric: a rejected entity-claim (name already claimed by a manual entity, another repository, or a removed entity) is persisted as a `ConflictRecord` and shown in Django admin (`admin.py`'s `ConflictRecordAdmin`) — but every other failure mode (connector fetch failure, YAML parse failure, manifest schema-validation failure, an unresolved reference inside a valid document, a duplicate ref declared twice within one repository) only reaches `logger.warning`/`logger.exception`. An operator has no admin-visible way to answer "is anything currently broken in this repository's manifests?" beyond those specific claim conflicts.

## Goals / Non-Goals

**Goals:**
- Let a `catalog-info.yaml` compose in additional YAML fragments with arbitrary filenames, organized however the repository owner wants (e.g. a `.manifests/` directory holding one fragment per concern), without requiring a directory-per-fragment.
- Keep manifest discovery's zero-coordination property intact: adding a new component's manifest must never require editing a file owned by someone else.
- Give ingestion failures that are not claim conflicts the same operator-visible, self-clearing treatment `ConflictRecord` already gives claim conflicts, without inventing a failure-type taxonomy up front.

**Non-Goals:**
- Replacing or relaxing the `**/catalog-info.yaml` discovery walk.
- A repository-wide, centrally-owned manifest index/ownership tree.
- Database-schema ingestion (separate change).
- Distinguishing failure *types* in the new admin-visible record (no `reason` enum) — v1 stores the message only.
- Preserving every simultaneous, independent failure for the same `(repository, path)` in the database (the application log remains the complete record; the DB record is "what's the latest known problem here").

## Decisions

### D1: `kind: Include` is document-level composition, not a discovery mechanism

An `Include` is just another raw document recognized inside the flat list `parsing.py` already produces from a `---`-separated file — not a new file-discovery rule. Concretely:

```yaml
# services/payments/catalog-info.yaml   (found by the existing tree-walk)
kind: Include
spec:
  paths:
    - .manifests/db-catalog-info.yaml
    - .manifests/*.yaml
---
apiVersion: atlas/v1alpha1
kind: Component
metadata:
  name: payments-service
...
```

This means: `Include` documents can appear anywhere in a multi-document file, interleaved with ordinary entity documents, with no special handling of "is this file an Include file" — each raw document is inspected independently.

**Alternatives considered:**
- *Relax discovery's filename match* (e.g. also match `**/manifests/*.yaml`) instead of introducing `Include`. Rejected: this is pure implicit scanning — a stray file dropped in a matching path is silently ingested, with no way to express "this fragment exists but isn't wired in yet." `Include` is opt-in: a fragment is inert until something references it.
- *Root-only manifest, walk removed, all composition via `Include`* (recursively, to delegate ownership per team in a monorepo). Rejected: this reintroduces a central-file coordination bottleneck — onboarding a new, independently-owned component would require editing a shared index file (or an index one level down owned by that component's own team, if recursion is used to delegate), where today it requires editing nothing but that component's own new file. The tree-walk's zero-touch property is worth more than the explicitness a root-only model would buy, so discovery is left untouched and `Include` is scoped to *local* composition within one already-discovered manifest.

### D2: Path resolution is relative to the including file's directory

`spec.paths` entries resolve against the directory containing the file that declares the `Include`, not the repository root and not the originating top-level `catalog-info.yaml` when includes nest. This keeps a component's own fragment set portable if its directory is renamed or moved, and keeps each `Include` declaration self-contained (readable without knowing the full repository layout).

### D3: Glob is supported

`.manifests/*.yaml` is allowed, not just explicit path lists. Accepted trade-off: a stray file matching the glob is silently ingested — judged acceptable because the blast radius is one component's own directory (this is local composition, not a repository-wide index), unlike the rejected "relax discovery globally" alternative in D1 where the blast radius is the whole repository.

### D4: Recursive, with cycle detection

An included fragment may itself contain `kind: Include` documents. The resolver tracks the set of repository-relative paths already visited in the current resolution chain; encountering a repeated path raises a specific, reported error (routed through `IngestionIssue`, see D6) rather than recursing until a stack limit or timeout. Recursion is included primarily for completeness/robustness against nested composition someone will eventually try, not because it's the primary use case — D1's rejection of a repository-wide `Include` tree means most real usage is expected to be shallow (one file, pulling in a handful of siblings).

### D5: Included fragments must not be named `catalog-info.yaml`

If an `Include` resolves to a path whose basename is `catalog-info.yaml`, that path would also be independently discovered by the tree-walk (D1), causing it to be ingested twice within the same run and rejected as a same-repository duplicate ref by the existing `_drop_duplicate_refs` (harmless but confusing). This is validated when a path is resolved and reported via `IngestionIssue` rather than only documented as a convention. A standalone pre-commit validator for repository owners to catch this before pushing is useful future work, left out of this change.

### D6: `IngestionIssue` is a new, separate, path-keyed model — not an extension of `ConflictRecord`

```python
class IngestionIssue(models.Model):
    repository = models.ForeignKey(
        "RegisteredRepository",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ingestion_issues",
    )
    repo_full_name = models.CharField(max_length=255)
    path = models.CharField(max_length=1024, blank=True)
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
```

Dedup/lifecycle follows `ConflictRecord`'s existing pattern in `upsert.py` (`_record_conflict`/`_resolve_conflicts`): find-or-create keyed on `(repository, path)`, refresh `message`/`last_seen`/`is_active=True` on recurrence, flip `is_active=False` once that `(repository, path)` completes a run without that failure. No typed `reason` — `message` is the same string that would otherwise only go to `logger.warning`/`.exception`.

**Alternatives considered:**
- *Extend `ConflictRecord`* by loosening `kind`/`namespace`/`name` to nullable and adding new `reason` choices. Rejected: `ConflictRecord` has its own settled `entity-claim-arbitration` spec built around a real `(kind, namespace, name)` identity; most of the failures this change surfaces (fetch failure, parse failure, an `Include` path that doesn't resolve) have no ref yet — the document that would have one was never successfully parsed/validated. Forcing them through a ref-shaped model would mean mostly-null rows and a spec that no longer matches its own model.
- *Typed `reason` enum on the new model.* Rejected for v1 as taxonomy-maintenance overhead without a clear present need; the exact log message already carries the information a human needs to act.
- *Fold the two ref-identified failures this change surfaces along the way — a duplicate ref declared twice in one repository (`pipeline.py`'s `_drop_duplicate_refs`), and an unresolved reference inside an otherwise-valid document (`upsert.py`'s `RefError` path) — into `IngestionIssue` too.* Rejected: both already have a real `(kind, namespace, name)` at the point they're raised, so they fit `ConflictRecord`'s existing shape (as new `reason` values) better than `IngestionIssue`'s path-keyed one. Left as plain logging in this change; a natural, explicitly-deferred follow-up (see proposal.md).

### D7: `(repository, path)` dedup key, not per-document or per-failure-type

A single multi-document file with two independent, simultaneous problems (e.g. one document fails schema validation, another has a malformed `Include`) collapses to one `IngestionIssue` row, and only the most recent message survives across runs. This was a deliberate simplicity choice: a richer key (e.g. including a per-document index or the attempted ref) would recover precision but starts reintroducing the structure D6 explicitly declined. The application log remains authoritative for "everything that happened this run"; `IngestionIssue` answers "is this path currently a problem," which a single row per path already answers.

## Risks / Trade-offs

- **[Silent multi-failure collapse]** → Mitigated by scope: this is a known, accepted v1 limitation (D7), not a bug; call it out in the admin help text / `IngestionIssueAdmin` if it proves confusing in practice.
- **[Glob-based `Include` silently ingesting a stray file]** → Mitigated by D3's scoping to local, single-component composition (small blast radius) plus D5's `catalog-info.yaml`-naming guard for the most likely accidental-duplication mistake; a future pre-commit validator (out of scope here) would close the remaining gap.
- **[Recursive `Include` cycles]** → Mitigated by D4's visited-path tracking; a cycle becomes a reported `IngestionIssue`, not a hang or crash.
- **[`IngestionIssue` table growth]** → Rows are upserted per `(repository, path)`, not appended per run, so growth is bounded by the number of distinct problematic paths across all registered repositories, not by run count. No retention/pruning policy is introduced in this change; revisit if resolved (`is_active=False`) rows accumulate unbounded over long deployments.
- **[`Include` expansion adding latency/fetch volume to a pass]** → Each `Include` triggers one `fetch_file` per resolved path, same cost model as an ordinary discovered manifest; no new risk beyond proportionally more files being fetched per repository, which is already unbounded by manifest count today.

## Migration Plan

1. Add `IngestionIssue` model + Django migration (additive; no change to existing models/migrations 0001–0004).
2. Implement `Include` document recognition and expansion in the parse/pipeline stage, gated on nothing (no plugin config flag) — a repository with no `Include` documents behaves identically to today.
3. Route the newly-added `Include` failure sites, plus the three existing silent sites named in the proposal (fetch failure, parse failure, validation failure), through `IngestionIssue` writes alongside their existing `logger.warning`/`.exception` calls (log output is unchanged, this is additive).
4. Register `IngestionIssueAdmin`.
5. No rollback complexity beyond a standard migration revert — `Include` is inert (unrecognized documents already fail validation and get skipped/logged today) if the feature is reverted, and `IngestionIssue` rows are additive/non-authoritative (no other code path reads them).

## Open Questions

- Should `IngestionIssue` eventually gain a retention policy (e.g. prune `is_active=False` rows older than N days), or is unbounded retention acceptable given rows are deduped per path rather than per run? Not blocking for this change.
- When the deferred `ConflictRecord` extension (duplicate ref / unresolved reference as new `reason` values, D6) is eventually done, should `IngestionIssue` and `ConflictRecord` be surfaced together in one combined admin view for operators, or is browsing two separate admin lists acceptable long-term?
