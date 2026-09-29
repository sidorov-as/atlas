## Context

Atlas has no implementation yet — this is pre-code design work. Entities can be created either manually via the web UI or via `catalog-info.yaml` ingestion (design.md §2), and [ADR 0001](../../../docs/adr/0001-yaml-is-source-of-truth.md) settles what happens when an already-ingested entity is re-ingested (full overwrite, UI read-only). It says nothing about the moment before that: a manual entity and a fresh YAML claim (or two different repos) declaring the same ref for the first time. Separately, entity identity today is just `kind` + `name`, globally unique, with no room for two teams to independently pick the same common name (`auth`, `gateway`, `frontend`) without a hard collision. This design implements both gaps, already recorded as the amendment to ADR 0001 and the new [ADR 0004](../../../docs/adr/0004-entity-identity-model.md).

## Goals / Non-Goals

**Goals:**
- Every ingestible entity (System, Component, Resource, API) tracks `source_kind` (`manual` | `yaml`) and, when `yaml`, which `RegisteredRepository` claims it.
- First-claim collisions are arbitrated deterministically and are never silent — a rejected claim is recorded and visible.
- A manual entity can be explicitly adopted into YAML control, one direction only.
- Entity identity is namespace-qualified (`kind` + `namespace` + `name`) with case-insensitive uniqueness, without exposing namespace anywhere in v1.
- Unregistering a `RegisteredRepository` is blocked while it still claims any entity, and never silently deletes, orphans, or reassigns what it claims.

**Non-Goals:**
- Field-level overlay/merge between manual edits and a re-ingested YAML file — considered and declined again; it answers PR-friction-at-scale, which this catalog is sized to not have (design.md §10).
- Exposing `namespace` in the UI or in `catalog-info.yaml` — deferred until a real collision at "tens of teams" scale makes it worth the surface area.
- A bulk "release all claimed entities" action, or a `yaml → yaml` repository-reassignment path — the only way to clear an unregistration block in v1 is deleting each claimed entity individually.
- `memberOf`/`hasMember` dual-declaration handling — not applicable here: resolved in `bootstrap-catalog-service` by modeling membership as a single `ManyToManyField`, so the two sides can't disagree in the first place (design.md §12).
- Group/User ingestion — decided against (design.md §8, §12): Group and User are admin-managed only, never ingested from YAML, so this change's `source_kind`/repository-FK/namespace additions correctly stay scoped to System/Component/Resource/API.

## Decisions

**`source_kind` + repository FK, not a source string.** System/Component/Resource/API gain a `source_kind` enum (`manual` | `yaml`) and a nullable FK to `RegisteredRepository`, set only when `source_kind=yaml`. A single string column (e.g. `"yaml:<owner>/<repo>"`) was considered and rejected: it can't express referential integrity, and it turns "what does this repo own" and repo-unregistration into a string-matching cleanup job instead of a real query.

**Namespace column, unexposed.** `namespace` defaults to `"default"`; uniqueness is enforced on `(kind, namespace, lower(name))`. Leaving identity flat (kind+name only, noted as an assumption) was rejected — retrofitting a namespace later changes what every ref string in every already-ingested `catalog-info.yaml` means, the one migration that reaches into other teams' repositories. Exposing it immediately was also rejected — nothing in the mockups or current scope needs two teams to deliberately share a name yet, and the arbitration rules below already turn a same-name collision into something survivable (a logged rejection, fixed by renaming) rather than something that needs a namespace escape hatch on day one. Case-insensitivity is explicit because Postgres's default collation is case-sensitive and Backstage's own uniqueness isn't — matching that avoids `component:Auth` / `component:auth` becoming two entities.

**Ingestion upsert arbitration.** Per ref in a manifest:

| Existing state | Ingestion action |
|---|---|
| Ref doesn't exist | Create, `source_kind=yaml`, repo FK set |
| `source_kind=manual` | Reject, record conflict |
| `source_kind=yaml`, same repo | Overwrite in full (ADR 0001, unchanged) |
| `source_kind=yaml`, different repo | Reject, record conflict |

Manual creation needs no equivalent branch — the `(kind, namespace, lower(name))` uniqueness constraint already rejects a manual create that collides with any existing entity, regardless of that entity's source.

**Conflicts are recorded, never just logged.** A dedicated conflict record (repository, ref, reason, first-seen, last-seen) is persisted and manageable in Django admin — the same pattern already used for `RegisteredRepository` itself (design.md §5) — plus a banner on the blocked entity's detail page naming the repository that couldn't claim it. Log-only was considered and rejected: for a small team, "my YAML silently does nothing" is a worse failure mode than a visible conflict, and a log line isn't discoverable from the UI.

**Conflicts are re-evaluated every run, never cached.** No processing-hash short-circuit skips the arbitration check on a run where nothing else changed. This is a deliberate design constraint, not an oversight to fix later: Backstage has hit exactly this bug class (a stale hash means deleting the blocking entity doesn't unblock the rival claim). The full re-scan is cheap at "a few hundred entities" (design.md §10), so there's no performance pressure to add the optimization that causes the bug.

**Intra-repo duplicates are rejected before any upsert.** A single ingestion run collects all `(kind, namespace, name)` pairs its manifests would emit before upserting any of them; a ref declared twice within the same run is rejected as a duplicate rather than resolved by whichever manifest happens to upsert last.

**Repository unregistration is blocked until nothing claims it.** A `RegisteredRepository` cannot be deleted/unregistered in Django admin while any entity still has `source_kind=yaml` with its repo FK pointing at it. Cascade-delete and orphan-and-keep (clearing `source_kind` back toward `manual`) were both considered and rejected: cascade risks leaving *other* entities' reference fields dangling (e.g. a Component's `dependsOn` pointing at a Resource just deleted by someone else's cascade), and orphaning is a system-triggered `yaml → manual`-shaped transition — the exact transition ADR 0001 forbids everywhere else, just arriving through a side door instead of the adopt endpoint. The only way to clear the block in v1 is deleting each claimed entity individually, via Django admin — YAML-managed entities already can't be deleted through the ordinary API (entity-catalog spec), so this cleanup was never going to be self-service anyway. Because registering, this cleanup, and unregistering are all Django-admin-only operations, no new permission model or API surface is needed.

**Conflict records snapshot the repository's identity, not just its FK.** `ConflictRecord.repository` stays a live FK for the common case, but the record also stores `repo_full_name` as a plain string at write time. This lets a `RegisteredRepository` be deleted once unregistration is unblocked (zero active claims) without either cascading away its conflict history or letting stale, already-resolved conflicts block the deletion.

**Adoption is one-directional, explicit, and permission-gated.** `POST /api/{kind}/{id}/adopt/` flips a manual entity's `source_kind` to `yaml` and sets the claiming repository, gated by the same owner-Group permission already used for editing (design.md §7) — no new permission model. It does not itself overwrite fields; the next ingestion run does that through the ordinary same-repo branch above. The reverse (`yaml` → `manual`) is never allowed: it would mean git stops being the sole source of truth for that entity, the core decision ADR 0001 makes. Automatic/silent adoption (e.g., a "trusted repo" auto-claiming a manual entity) was considered and rejected — it breaks the "arbitrate, never silently mutate" principle running through this whole design.

## Risks / Trade-offs

- [Risk] A team that migrates a service to GitOps and expects it to "just work" hits a rejected claim instead → Mitigation: the banner on the blocked entity names the repository and is visible to exactly the people (owner Group members) who can resolve it via adopt.
- [Risk] Shipping arbitration without the adopt endpoint (staged rollout) would leave the common manual→GitOps migration path with no resolution → Mitigation: arbitration, conflict visibility, and the adopt endpoint ship together in this change, not staged.
- [Risk] The namespace uniqueness constraint has to be correct from the first migration, since tightening `(kind, namespace, lower(name))` after entities exist is a cleanup job → Mitigation: no risk in practice here — Atlas has no existing data, so this ships as part of the initial schema, not a retrofit.
- [Trade-off] No dedicated "conflicts" page in the web UI — conflict records are Django-admin-only in v1, consistent with how `RegisteredRepository` itself is managed. Acceptable at "tens of teams" scale; revisit if conflict volume makes admin-only visibility impractical.
- [Trade-off] Unregistering a repository that claims many entities means deleting them one at a time in Django admin — no bulk "release all" action in v1. Accepted for the same "no silent state change" reason as the rest of this design; revisit if decommissioning a whole System this way becomes a frequent, painful operation.

## Migration Plan

Not applicable — Atlas has no existing implementation or production data. `source_kind`, the repository FK, the conflict record model, and the `namespace` column all ship as part of the initial entity schema rather than as a migration against live data.

## Open Questions

None currently open for this change.
