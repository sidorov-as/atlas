## Why

Today, whole catalog entities (System/Component/Resource/API) have no soft-decommission path — only hard delete, blocked by dependency checks. This causes a real, already-occurring bug: when a repo's `catalog-info.yaml` stops declaring an entity it previously declared, the entity itself is never touched (it stays active forever, still locked read-only since `source_kind=yaml` rejects manual edits) while the same ingestion pass *does* prune its YAML-origin relationships — producing a "zombie" entity that looks fully active and healthy but has silently lost its architecture edges, with no way for anyone to fix or even flag it. Separately, `ApiEndpoint`/`ApiOperation` already have their own narrower `active`/`removed` soft-delete mechanism, so the catalog currently ships two different, inconsistent soft-delete models. And nothing today prevents a same-named entity from silently reusing an old identity, or guarantees a decommissioned entity's status is visible to anything that still references it — exactly the misleading, inconsistent behavior this change closes off.

## What Changes

- Introduce `Removed` as a single, uniform soft-delete state for CatalogEntity kinds (System/Component/Resource/API), unifying with — and extending — the existing ApiEndpoint/ApiOperation `active`/`removed` mechanism rather than inventing a second word ("archived") for an adjacent concept.
- Add `Revive` (Removed → active, same identity/id preserved): automatic on re-declaration from the same origin (YAML re-ingestion, re-resolved spec), plus an explicit manual Revive action for manually-removed entities.
- Add `Purge`: a new, explicit, destructive action reachable only from `Removed` (never directly from active) that frees the `(kind, namespace, name)` slot for reuse by a genuinely new entity (new id, no inherited history). Blocked by any active reference, including non-FK ref-string references (Flow `query_ref`/`event_ref`); cascades cleanup of purely-Removed-status references.
- Add `Purge Grant`, a permission scoped per owner-Group (plus a global-admin override), carving out YAML-managed entities from the existing "no manual writes on `source_kind=yaml`" rule for this one destructive action — this also resolves the existing tension where repository unregistration requires deleting each claimed entity individually.
- **BREAKING (bug fix)**: fix ingestion's zombie-entity bug — a whole entity missing from a re-ingested manifest now becomes `Removed` (not silently left active forever), symmetric to how ingestion already reconciles relationships and Endpoints/Operations. Auto-remove authority is sticky to the entity's own origin (an ingestion source can never auto-remove an entity it didn't create).
- Extend `ApiEndpoint`/`ApiOperation` with the same `Purge` action, for consistency with the new whole-entity model (today they are permanently soft-only).
- Add a manual `deprecated` boolean override on `ApiOperation`, since AsyncAPI has no native deprecated keyword (unlike OpenAPI) and deprecated-propagation would otherwise be asymmetric between the two protocols.
- Propagate `removed` (new) and `deprecated` (existing, previously entity-page-only) status as visible warnings into everything that references an entity: derived relations, Architecture Relationships, Linked-Services/consumers views, and Flow steps (`entity_ref` steps gain the same live-status surfacing `query_ref`/`event_ref` steps already have).
- Reject a rival claim against a `Removed` entity's name with a new, specific `removed_entity` ConflictRecord reason instead of a generic conflict.
- Block removing an owning Group/Actor while it still owns active entities (treat `owner` as a protected reference like any other).
- Add a read-only "History" section on the entity detail page surfacing Remove/Revive/Purge audit events (Remove/Revive/Purge route through the existing Entity Service transaction, so they get `EntityAuditRecord`s for free — but that data needs to be user-visible, not just internal).
- Explicitly document that DB schema stays a single-blob facet with no per-column lifecycle in this release (the containing Resource participates in the standard lifecycle; individual tables/columns do not).
- **BREAKING (UX correction after initial ship)**: retire the plain `Delete` action (REST route and UI affordance) for System/Component/Resource/API — seeing it alongside the new `Remove` in the action menu read as two competing paths to the same destructive outcome, so `Remove` → `Purge` is now the only way to permanently destroy one of these four kinds. Deleting a zero-reference entity now requires a Purge Grant, not just owner-Group membership.

## Capabilities

### New Capabilities

- `entity-removal-lifecycle`: the `Removed`/`Revive`/`Purge` state machine for CatalogEntity kinds (System/Component/Resource/API) — states, transitions, container-level scope (children removed implicitly with their parent), Purge's reference-scanning validation (FK-backed and ref-string-backed), the Purge Grant permission model, and the entity-detail "History" tab.

### Modified Capabilities

- `entity-lifecycle-service`: Remove/Revive/Purge are added as transaction types that flow through the same single Entity Service transaction as create/update/delete.
- `entity-catalog`: default list/search views hide `Removed` entities behind an explicit, ungated "show removed" toggle; CRUD requirements note where Remove/Revive/Purge fit relative to the existing YAML-managed write block; plain `Delete` is retired in favor of `Remove` → `Purge` as the only destructive path.
- `catalog-ingestion`: fixes the zombie-entity bug — entity-level reconciliation (an entity missing from a re-ingested manifest becomes `Removed`, revives on reappearance), with auto-remove authority sticky to origin.
- `entity-claim-arbitration`: a `Removed` entity's ref still blocks a rival claim; new `removed_entity` ConflictRecord reason.
- `catalog-auth`: adds the per-owner-group-scoped Purge Grant permission (plus global-admin override); clarifies that Remove/Revive follow the existing ownership-based edit permission.
- `api-endpoints`: `Endpoint` gains `Purge` (today permanently soft-only).
- `api-operations`: `Operation` gains `Purge`; `ApiOperation` gains a manual `deprecated` boolean override for AsyncAPI.
- `endpoint-service-dependencies`: Linked Services/consumers views also warn for a `deprecated` Endpoint (today only `removed` is covered).
- `operation-service-dependencies`: same, for a `deprecated` Operation.
- `entity-relations`: relation entries surface the target entity's `removed`/`deprecated` status.
- `architecture-relationships`: Architecture Relationship listings surface a removed-target warning.
- `flow-management`: `entity_ref`-targeted steps gain the same live removed/deprecated status surfacing that `query_ref`/`event_ref` steps already have, plus a visible diagram indicator.

## Impact

- Backend: `CatalogEntity` gains a `status` field (or equivalent) and Remove/Revive/Purge service methods in the Entity Service; `ApiEndpoint`/`ApiOperation` gain a `Purge` method; ingestion's upsert/reconciliation path (`upsert.py`) gains entity-level diffing; `ConflictRecord` gains a `removed_entity` reason; a new `PurgeGrant`-style permission model (per-owner-Group + global-admin override); `owner` FK behavior gains a dependency check; the Entity Service's `delete()` method and the four kinds' REST `DELETE` routes are removed.
- Frontend: entity list/search views gain a "show removed" toggle; entity detail pages gain Remove/Revive/Purge actions (replacing Delete) and a History tab; relation, Architecture Relationship, Linked Services, and Flow-diagram rendering gain removed/deprecated warning indicators.
- Docs: explicit documentation of the manual-vs-YAML remove/revive asymmetry and the DB-schema per-column lifecycle non-goal.
- No change to DB schema's single-blob facet model itself.
