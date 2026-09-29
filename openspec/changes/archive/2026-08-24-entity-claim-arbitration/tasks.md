## 1. Entity identity model

- [x] 1.1 Add a `namespace` field (default `"default"`) to the entity base shared by System, Component, Resource, API
- [x] 1.2 Add a unique constraint on `(kind, namespace, lower(name))` — case-insensitive
- [x] 1.3 Implement the ref parser: `[kind:][namespace/]name` → `(kind, namespace, name)`, defaulting an absent namespace to `default`
- [x] 1.4 Reject `/` in `metadata.name` during manifest validation

## 2. Source tracking & conflict data model

- [x] 2.1 Add a `source_kind` field (`manual` | `yaml`) to System, Component, Resource, API
- [x] 2.2 Add a nullable FK from each of those kinds to `RegisteredRepository`, set only when `source_kind=yaml`
- [x] 2.3 Add a conflict record model (repository FK, `repo_full_name` string snapshot, kind, namespace, name, reason, first_seen, last_seen)
- [x] 2.4 Register the conflict record model in Django admin

## 3. Ingestion arbitration

- [x] 3.1 Collect all `(kind, namespace, name)` refs a run would emit before upserting any of them; reject and log intra-repo duplicates
- [x] 3.2 Upsert branch: ref doesn't exist → create with `source_kind=yaml`, repo FK set
- [x] 3.3 Upsert branch: existing `source_kind=manual` → reject, create/update conflict record
- [x] 3.4 Upsert branch: existing `source_kind=yaml`, same repo → overwrite entity in full (ADR 0001)
- [x] 3.5 Upsert branch: existing `source_kind=yaml`, different repo → reject, create/update conflict record
- [x] 3.6 Ensure arbitration re-evaluates from current state on every run — no processing-hash short-circuit skips the conflict check

## 4. Conflict visibility

- [x] 4.1 Resolve and clear a conflict record's currency once its blocking claim stops recurring (still visible historically, but not surfaced as active)
- [x] 4.2 Include active-conflict info in an entity's detail response so the frontend can render the "blocked by `org/repo`" banner
- [x] 4.3 Frontend: render the blocked-by-conflict banner on the entity detail page, styled distinctly from the existing read-only "managed by `catalog-info.yaml`" banner (`catalog-web-ui` spec delta)

## 5. Adoption endpoint

- [x] 5.1 Add `POST /api/{kind}/{id}/adopt/` accepting a target `RegisteredRepository`
- [x] 5.2 Enforce owner-Group-membership-or-superuser permission (reuse the existing edit-permission check, design.md §7)
- [x] 5.3 On success, set `source_kind=yaml` and the repo FK; do not modify any other field
- [x] 5.4 Reject any request that would set `source_kind` from `yaml` back to `manual`, regardless of caller

## 6. Repository unregistration

- [x] 6.1 Block deleting/unregistering a `RegisteredRepository` in Django admin while any entity has `source_kind=yaml` with its repo FK pointing at it
- [x] 6.2 Surface a clear admin-facing message listing (or counting) the entities still claiming the repository, so the operator knows what to delete first
- [x] 6.3 Populate `repo_full_name` on conflict records at write time, independent of the live `repository` FK
- [x] 6.4 Allow `RegisteredRepository` deletion once zero entities claim it, regardless of how many historical (non-active) conflict records reference it

## 7. Tests

- [x] 7.1 Ref parsing and case-insensitive uniqueness (entity-identity spec scenarios)
- [x] 7.2 Each ingestion arbitration branch, including the no-existing-entity and same-repo-overwrite cases (entity-claim-arbitration spec scenarios)
- [x] 7.3 Deleting a blocking manual entity unblocks the rival YAML claim on the very next run, with no manual cache-clearing step
- [x] 7.4 Intra-repo duplicate ref within a single run is rejected for both declarations
- [x] 7.5 Adopt endpoint: permission enforcement (403 for non-owners), one-directional constraint (yaml→manual always rejected), and that the next ingestion run performs the actual field overwrite
- [x] 7.6 Unregistering a `RegisteredRepository` that still claims an entity is rejected; unregistering succeeds once all claimed entities are deleted
- [x] 7.7 Deleting a `RegisteredRepository` with only historical (resolved) conflicts succeeds, and those conflict records still display the repository's name via the snapshot field
- [x] 7.8 Blocked-by-conflict banner renders on a blocking entity's detail page and is visually distinct from the read-only YAML-managed banner; neither banner renders when there's no active conflict (catalog-web-ui spec scenarios)
