## 1. Backend: expose target identity on relations

- [x] 1.1 In `apps/catalog/relations.py`, change `entity_relations()` to return `(predicate, target_ref, target_kind, target_id)` instead of `(predicate, target_ref)`, using the `target` object it already fetches.
- [x] 1.2 In `apps/catalog/api/schemas.py`, add `targetKind: str` and `targetId: int` fields to `RelationOut`.
- [x] 1.3 In `apps/catalog/api/views.py`, update `_relations_out()` to populate the new fields from the updated `entity_relations()` return shape.
- [x] 1.4 Update/extend `apps/catalog/tests/test_relations.py` to assert `targetKind`/`targetId` are present and correct on a relations response (e.g. the existing `dependsOn`/`ownedBy` scenarios).

## 2. Frontend: shared ref-link building block

- [x] 2.1 Add a `kindToPath` map (system/component/resource/api/group → their list-page path prefixes; no entry for `user`) alongside the existing entity API helpers (e.g. in `lib/entities.ts`).
- [x] 2.2 Add a small helper/component that renders a relation's target as a `Link`-to-detail-page when its kind is in `kindToPath`, falling back to plain text otherwise (covers the `user` case defensively).
- [x] 2.3 Update `frontend/src/lib/types.ts`'s `Relation` type to include `targetKind`/`targetId`.

## 3. Frontend: make Relations tab rows clickable

- [x] 3.1 Update `RelationsTab.tsx` to render the Target column using the helper from 2.2, navigating to `kindToPath[targetKind]/targetId` on click.
- [x] 3.2 Verify this on all four detail pages that embed `RelationsTab` (System, Component, Resource, API) — each shows working links in its Relations tab.

## 4. Frontend: Component's Provides/Consumes API links

- [x] 4.1 In `ComponentDetailPage.tsx`, replace the `RefList`-based Provides API / Consumes API sections with data from `componentsApi.relations(component.id)`, filtered to the `providesAPI` and `consumesAPI` predicates respectively.
- [x] 4.2 Render each entry using the helper from 2.2 (link to the API's detail page).
- [x] 4.3 Confirm `dependsOn` (unaffected by this change) still renders as before via `RefList`.

## 5. Frontend: related-entity table row navigation

- [x] 5.1 Wire `useEntityRowActivation` into `ChildTable` (`SystemDetailPage.tsx`), passing `onOpenDetail` to navigate to the clicked entity's detail route, and pass `onRowClick={handleRowClick}` to its `EntityTable`.
- [x] 5.2 Do the same for Team's `OwnedTable` (`TeamDetailPage.tsx`) ahead of/alongside its rebuild in section 6.
- [x] 5.3 Manually verify double-click navigation on: a System's Components/Resources/APIs tabs, and a Team's owned-entity tabs.

## 6. Frontend: rebuild TeamDetailPage on EntityDetailPage

- [x] 6.1 Replace `TeamDetailPage`'s bespoke layout with `EntityDetailPage`, passing breadcrumb, `teamRailFields`, `links`, and tabs.
- [x] 6.2 Build the tab list: Overview (markdown description), Members (member list), Systems/Components/Resources/APIs (each using the row-navigation-enabled `OwnedTable` from section 5, filtered by `owner: group:{name}`).
- [x] 6.3 Remove now-dead layout code specific to the old two-column stacked design (keep `OwnedTable` itself — it's reused inside the new tabs).
- [x] 6.4 Confirm `EntityDetailPage`'s manual-vs-YAML-managed Edit/Delete affordances don't misfire for Groups (Groups have no edit/delete route — pass whatever no-op/guard `EntityDetailPage` expects, matching how it's already handled for other read-only cases).

## 7. Verification

- [x] 7.1 Run backend tests (`apps/catalog/tests/test_relations.py` and any API-level tests covering `/relations/` responses).
- [x] 7.2 Run frontend tests (`ApiDetailPage.test.tsx` and any test touching `RelationsTab`/`ComponentDetailPage`/`TeamDetailPage`).
- [x] 7.3 Manual pass in the browser: System → Resources tab double-click, Component → Provides/Consumes API links, Component/System/Resource/API → Relations tab links, Team detail page tabs + rail + double-click navigation on owned-entity tabs.

## 8. Backend: expose owner/system id on entity responses

- [x] 8.1 In `apps/catalog/api/schemas.py`, add `owner_id: int` to `SystemSpecOut`/`ComponentSpecOut`/`ResourceSpecOut`/`ApiSpecOut`, and `system_id: int | None` to `ComponentSpecOut`/`ResourceSpecOut`/`ApiSpecOut`.
- [x] 8.2 In `apps/catalog/api/views.py`, populate the new fields from `instance.owner.id` and `instance.system.id` (guarding Resource's nullable `system` the same way its `system` ref is already guarded: `instance.system.ref if instance.system_id else None`).
- [x] 8.3 Update/extend backend tests covering System/Component/Resource/API responses to assert `ownerId`/`systemId` are present and correct.

## 9. Frontend: rail Owner/System links

- [x] 9.1 Add `ownerId: number` to `SystemSpec`/`ComponentSpec`/`ResourceSpec`/`ApiSpec`, and `systemId: number | null` to `ComponentSpec`/`ResourceSpec`/`ApiSpec` in `frontend/src/lib/types.ts`.
- [x] 9.2 In `lib/railFields.tsx`, render Owner (all four kinds) and System (Component/API always; Resource when present) via `RelationTargetLink` inside the existing `Label` chip, instead of plain `refName(...)` text. Resource's System field keeps its '—' fallback when `system` is absent.
- [x] 9.3 Manually verify: System/Component/Resource/API detail page rail Owner links to the Team; Component/API rail System links to the System; a Resource with a System shows a working link, one without still shows a plain dash.

## 10. Verification

- [x] 10.1 Run backend tests covering System/Component/Resource/API responses.
- [x] 10.2 Run frontend tests.
- [x] 10.3 Manual pass in the browser confirming rail Owner/System links on all four kinds, including the Resource-with-no-System dash case.
