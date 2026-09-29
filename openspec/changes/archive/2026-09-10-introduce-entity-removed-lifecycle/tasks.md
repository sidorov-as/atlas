## 1. Ingestion zombie-entity bug fix (highest priority — flagged separately per user request, ships independently of the rest)

- [x] 1.1 In the ingestion upsert/reconciliation path (`upsert.py`), add entity-level diffing symmetric to the existing relationship and Endpoint/Operation reconciliation: for each `RegisteredRepository`, after a run, find every `source_kind=yaml` entity it claims whose ref was not seen in this run's manifests.
- [x] 1.2 For each such entity, invoke the Entity Service's Remove transaction (not a direct status write) — do not touch entities claimed by a different repository or `source_kind=manual` entities (auto-remove authority sticky to origin, per `catalog-ingestion`'s new requirements).
- [x] 1.3 When a manifest re-declares a ref whose currently-claimed entity is `removed`, invoke Revive (same repo, same ref) before applying the normal same-repo overwrite, preserving id and non-pruned relations.
- [x] 1.4 Write/extend tests: a dropped declaration removes (not zombifies) the entity; a re-added declaration revives it; a manually-created entity sharing an unclaimed ref is untouched; one repo's reconciliation never affects a different repo's claim.
- [x] 1.5 Note in the release notes / migration doc that this is a genuine behavior change for existing deployments (previously-"stuck-active" zombie entities will become `removed` on next ingestion run).

## 2. Data model: Removed/Revive/Purge core

- [x] 2.1 Add `status` (`active`/`removed`, default `active`) to `CatalogEntity` (or the shared identity model), migrated with all existing rows defaulting to `active`.
- [x] 2.2 Add a `PurgeGrant`-style model or permission scoped per owner-Group (who granted it, to whom, for which Group), plus recognition of global-admin status as an override.
- [x] 2.3 Add a `removed_entity` reason to the `ConflictRecord` reason enum, alongside existing `manual_entity`/`other_repository`.
- [x] 2.4 Add `owner` protected-reference validation (block deleting a Group/Actor that still owns any `active` entity), reusing the existing `validate_delete`-style dependency-check pattern.

## 3. Entity Service: Remove/Revive/Purge transactions

- [x] 3.1 Add Remove, Revive, and Purge as transaction types on the Entity Service, each running authorize → validate → mutate → audit → commit in one transaction, per the modified `entity-lifecycle-service` requirements.
- [x] 3.2 Remove: sets `status=removed`; blocked for `source_kind=yaml` entities when invoked manually (only ingestion reconciliation, task 1.2, may remove a YAML-managed entity).
- [x] 3.3 Revive: sets `status=active`, preserving id/relations/audit history; manual Revive is blocked for `source_kind=yaml` entities, same as manual Remove (D13) — a YAML-managed `removed` entity can only revive via ingestion reconciliation, never a manual Revive action; manual Revive is available only for `source_kind=manual` entities.
- [x] 3.4 Purge: permission-checks the Purge Grant (owner-Group-scoped or global-admin) regardless of `source_kind`; scans FK-backed references (`dependsOn`, `providesApis`, `consumesApis`, `owner`) AND ref-string-backed references (Flow `entity_ref`/`query_ref`/`event_ref`) for anything still active; blocks with a named list if any are active; cascades cleanup of purely-removed-status references otherwise; deletes the `CatalogEntity` row and kind-details row.
- [x] 3.5 Implement Purge's reference scan as an extensible/registered check (not hardcoded to Flow) so future non-FK reference mechanisms can register their own scan, per design.md's mitigation for the ref-string blind-spot risk.
- [x] 3.6 Wire REST endpoints: remove/revive/purge actions per kind (System/Component/Resource/API), following the existing per-kind viewset pattern.
- [x] 3.7 Tests: active→purge rejected; remove→purge with no references succeeds; remove→purge blocked by active FK reference; remove→purge blocked by active Flow entity_ref; remove→purge succeeds and cascades when all references are removed; purged name is claimable by a new entity with a new id.

## 4. Claim arbitration: removed_entity conflict

- [x] 4.1 Update claim arbitration to treat a `removed` entity's ref as still claimed, rejecting a rival claim with the new `removed_entity` ConflictRecord reason.
- [x] 4.2 Update the conflict-banner UI to render the `removed_entity` reason's specific message (naming the repository/entity and instructing revive-or-purge), per `entity-claim-arbitration`'s new requirements.
- [x] 4.3 Update repository-unregistration blocking logic/messaging to reflect the new Remove→Purge-with-grant path as the way to clear claimed entities (both active and removed) ahead of unregistration.
- [x] 4.4 Tests: rival claim against a removed entity is rejected with `removed_entity` reason; claim succeeds immediately after the blocking entity is purged, with no cache-invalidation step; repository unregistration still blocked while removed (unpurged) entities remain claimed.

## 5. Endpoint/Operation Purge and AsyncAPI deprecated override

- [x] 5.1 Add a Purge action to `ApiEndpoint`, gated the same way as whole-entity Purge, scanning `ServiceEndpointUsage` links; add matching tests.
- [x] 5.2 Add a Purge action to `ApiOperation`, gated the same way, scanning `ServiceOperationUsage` links; add matching tests.
- [x] 5.3 Add a manual `deprecated` boolean field to `ApiOperation` (default `false`), settable via Django admin, not overwritten by AsyncAPI re-import; add matching tests.

## 6. Propagation: relations, architecture relationships, linked services, flow

- [x] 6.1 `GET /api/{kind}/{id}/relations/`: include target `status`/`deprecated` in each relation entry.
- [x] 6.2 Architecture Relationship listings: include source/target `status`/`deprecated` in each entry.
- [x] 6.3 Endpoint Linked Services tab/consumers graph: add the deprecated-endpoint warning, distinguished visually from the existing removed-endpoint warning.
- [x] 6.4 Operation Linked Services tab: add the deprecated-operation warning, distinguished visually from the existing removed-operation warning.
- [x] 6.5 Flow read path: resolve and include live `status`/`deprecated` for `entity_ref`-targeted steps at read time, mirroring the existing `query_ref`/`event_ref` live-status resolution; do not mutate the stored `entity_ref`.
- [x] 6.6 Flow diagram (detail page and edit canvas): render a visible, distinguishable warning indicator on a step node whose resolved reference is `removed` or `deprecated`.
- [x] 6.7 Component/System detail pages: surface removed/deprecated warnings wherever `dependsOn`/`providesApis`/`consumesApis`/`hasPart` targets are rendered, consuming the new relation-entry fields from 6.1.
- [x] 6.8 Tests for each of the above surfaces: removed target warns, deprecated target warns, active/non-deprecated target shows no warning, purged (fully gone) target doesn't crash the read.

## 7. Entity detail UI: lifecycle actions, list toggle, History tab

- [x] 7.1 Add Remove/Revive/Purge actions to the entity detail page's action menu, visible/enabled per the permission rules in `catalog-auth` (ownership for remove/revive, Purge Grant for purge), hidden entirely (not just disabled) when unavailable, consistent with this codebase's existing permission-gated-and-hidden pattern (e.g. Link/Unlink actions).
- [x] 7.2 Add a "show removed" toggle to System/Component/Resource/API list and search views, open to any authenticated viewer, off by default.
- [x] 7.3 Add a read-only History tab/section to the entity detail page, sourced from `EntityAuditRecord`s, showing Remove/Revive/Purge (and existing create/update/delete) events with actor and timestamp.
- [x] 7.4 Tests: actions appear/disappear per permission; show-removed toggle reveals removed entities to a non-owner; History tab renders remove-then-revive sequence correctly.

## 8. Documentation

- [x] 8.1 Add ADR `local/docs/adr/0026-<slug>.md` capturing the Removed/Revive/Purge decision (terminology, identity-on-reuse, container-level scope, Purge Grant scoping) — reuse design.md's Decisions section as source material.
- [x] 8.2 Update `CONTEXT.md`'s Language section with `Removed`, `Revive`, `Purge`, and `Purge Grant` term definitions, consistent with the existing glossary's style (definition + `_Avoid_` line).
- [x] 8.3 Document the manual-vs-YAML remove/revive asymmetry explicitly (manual entities require explicit action; YAML entities reconcile automatically) so it isn't assumed to be automatic staleness detection.
- [x] 8.4 Document the DB-schema per-column lifecycle Non-Goal explicitly: `DatabaseSchema` stays a single-blob facet with no per-column removed/revive/purge in this release; only the containing Resource participates in the standard lifecycle.

## 9. End-to-end verification

- [x] 9.1 Walk through the settled scenario table from the design conversation (repo drops a declaration → removed; repo re-declares → revived; a different repo tries to claim the same name while removed → rejected with `removed_entity`; a mistakenly-created entity with no references is removed then purged trivially; a removed entity still referenced is purge-blocked; a removed entity referenced only by removed things purges with cascade) as an integration test suite.
- [x] 9.2 Confirm `openspec validate introduce-entity-removed-lifecycle --strict` passes and run the full test suite before archiving this change.

## 10. UX revisit: retire plain Delete; close the parent-removed visual gap (D14)

Raised after the initial implementation shipped: seeing `Remove` next to the pre-existing `Delete` in the action menu read as two competing paths to the same outcome (D14), and a removed System's Components/Resources/APIs tabs gave no visual signal that their parent was gone (D10's data-model decision was correct; the display side of it was incomplete).

- [x] 10.1 Retire plain Delete for System/Component/Resource/API: remove the `delete()` REST method from the four kinds' detail controllers (DELETE now 405s), remove the now-unused `EntityService`-backed `delete_entity()` REST wrapper and its exports, keep `EntityService.delete()`/`validate_delete()`/`delete_blocked()` intact (still load-bearing for Group/Actor owner-protection and Purge's backstop check).
- [x] 10.2 Frontend: drop the `Delete` button and `onDelete` prop from `EntityDetailShell`; rename `{kind}Api.softRemove` to `{kind}Api.remove` now that the hard-delete method of the same name is gone; update the four detail pages and `EntityListPage`'s row-action confirm copy/behavior (hidden for already-removed rows) to match.
- [x] 10.3 Add a "Removed" badge to the entity detail header (previously the only signal was which action buttons appeared).
- [x] 10.4 Close the parent-removed visual gap on a System's Components/Resources/APIs child tabs: a banner when the parent System is removed, plus the same "show removed" toggle the top-level list pages have (children's own `status` still isn't cascaded — D10 stands — only the display gap closes).
- [x] 10.5 Update design.md (D14 + Non-Goals), proposal.md, and the `entity-catalog` delta spec (drop `delete` from the CRUD requirements' text/scenarios, add the "no DELETE route" scenario) to match.
- [x] 10.6 Tests: REST DELETE returns 405 for all four kinds; Remove/Revive/Purge/Delete button visibility per status/YAML-managed; Removed badge renders; parent-removed banner and show-removed toggle on child tabs; row-action Remove confirm copy and removed-row hiding. Full test suite green (587 backend, 343/344 frontend — the one frontend failure is pre-existing and unrelated, `TeamsListPage.test.tsx`'s CSS-width assertion).
