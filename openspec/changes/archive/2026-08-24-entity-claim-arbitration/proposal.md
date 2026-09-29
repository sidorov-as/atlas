## Why

Atlas entities can be created either manually via the web UI or via `catalog-info.yaml` ingestion (design.md §2), but [ADR 0001](../../../docs/adr/0001-yaml-is-source-of-truth.md) only specifies precedence for *re-ingesting a file already tied to an entity* — it says nothing about the first-claim collision between a manual entity and a fresh YAML claim (or two different repos claiming the same ref). Left unresolved, that collision either silently overwrites a team's manual work or silently produces a duplicate entity. Separately, entity identity today is just `kind` + `name`, globally unique with no escape hatch — at "tens of teams" scale, common names (`auth`, `gateway`, `frontend`) are genuinely likely to collide across unrelated repos. Both gaps need to be closed before ingestion can be built safely.

## What Changes

- Add a `source_kind` (`manual` | `yaml`) field and a nullable FK to `RegisteredRepository` on every ingestible entity kind (System, Component, Resource, API).
- Ingestion upsert arbitrates first-claim collisions instead of silently overwriting: reject (with a recorded conflict) if the ref is already claimed by a manual entity or by a different repo; overwrite in full only when the same repo re-claims its own entity (unchanged from ADR 0001).
- Record conflicts (repo, ref, reason, first/last seen), visible in Django admin, with a banner on the blocked entity's detail page naming the repo that couldn't claim it.
- Reject intra-repo duplicate refs within a single ingestion run — all `(kind, namespace, name)` pairs a run would emit are collected before any upsert executes.
- Never cache or short-circuit the conflict check across runs — every run re-evaluates from scratch.
- Add `POST /api/{kind}/{id}/adopt/`: flips a manual entity's `source_kind` to `yaml`, claimed by a named repo, gated by the same owner-Group permission used for editing (design.md §7). One direction only — a YAML-managed entity can never be adopted back to manual. The endpoint only flips state; the next ingestion run performs the actual field overwrite via the ordinary upsert path.
- Add a `namespace` column (default `"default"`) to entity identity, with a uniqueness constraint on `(kind, namespace, lower(name))` (case-insensitive). Entity refs are parsed as `[kind:][namespace/]name` from day one, resolving an absent namespace to `default`. Not exposed in the web UI or in `catalog-info.yaml` in v1 — see [ADR 0004](../../../docs/adr/0004-entity-identity-model.md).
- Block `RegisteredRepository` unregistration in Django admin while it still claims any entity; the only way to clear the block is deleting each claimed entity individually (no cascade-delete, no orphan-and-keep, no repository reassignment). Conflict records store a `repo_full_name` snapshot alongside their live repository FK, so conflict history survives a repository being deleted once unblocked.

No **BREAKING** changes — Atlas has no existing implementation yet; this establishes the identity and ingestion-arbitration model before the entity data layer is built.

## Capabilities

### New Capabilities
- `entity-claim-arbitration`: how an entity ref first gets assigned a `source_kind`, how first-claim collisions between manual and YAML (or between two repos) are arbitrated and recorded, and how a manual entity can be explicitly adopted into YAML control.
- `entity-identity`: the `namespace`-qualified identity model entities are keyed by (`kind` + `namespace` + `name`), including case-insensitive uniqueness and ref parsing, kept unexposed in v1.

### Modified Capabilities
- `catalog-web-ui` (established by `bootstrap-catalog-service`, which this change depends on landing first): adds the "blocked by conflict" banner to the entity detail page, distinct from that change's existing read-only "managed by `catalog-info.yaml`" banner.

## Impact

- **Data model**: new `source_kind` + repo FK columns on System/Component/Resource/API; new `namespace` column and `(kind, namespace, lower(name))` uniqueness constraint on the same kinds; a new conflict-record table/model with a `repo_full_name` snapshot field.
- **Ingestion pipeline**: the management-command upsert logic gains the arbitration branch, run-scoped duplicate collection, and no caching of the conflict check.
- **REST API**: new `POST /api/{kind}/{id}/adopt/` endpoint across the ingestible kinds.
- **Django admin**: conflict records become visible/manageable there, alongside the existing `RegisteredRepository` admin (design.md §5); deleting/unregistering a `RegisteredRepository` is blocked while it still claims any entity.
- **Web UI**: entity detail pages (built by `bootstrap-catalog-service`) gain a conflict banner — see `catalog-web-ui` under Modified Capabilities.
- **Permissions**: the adopt endpoint reuses the existing owner-Group edit permission (design.md §7) — no new permission model.
- **Docs**: formalizes decisions already captured in `docs/design.md` (§3, §5, §6, §8, §12), `docs/adr/0001-yaml-is-source-of-truth.md` (amendment), and `docs/adr/0004-entity-identity-model.md`.
