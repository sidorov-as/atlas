## Why

Entity detail pages have three related navigation gaps: related-entity tables (e.g. a System's Resources tab, a Team's owned-entity sections) don't support double-click-to-navigate like every top-level list page does; ref fields that point at another entity (Component's Provides/Consumes API, and every Relations tab's target column) render as plain unlinkable text because the id needed to route to them was never exposed by the API; and the Team detail page is a bespoke layout that doesn't match the shared chrome every other entity detail page uses, making its stacked Members/Systems/Components/Resources/APIs sections hard to visually parse.

## What Changes

- Wire the existing `useEntityRowActivation` hook into `ChildTable` (System's Components/Resources/APIs tabs) and Team's `OwnedTable`, so a fast second click on a row navigates to that entity's detail page — matching the behavior `EntityListPage` and `TeamsListPage` already have.
- Extend the `GET /api/{kind}/{id}/relations/` response (`RelationOut`) with `targetKind`/`targetId` alongside the existing `target` ref string, sourced from the object `entity_relations()` already resolves internally.
- Make Relations tab rows clickable (System/Component/Resource/API detail pages): a row navigates to its target entity's detail page, using the new `targetKind`/`targetId`.
- Replace Component's Provides API / Consumes API display: instead of rendering the unlinkable `spec.providesApis`/`consumesApis` ref arrays as plain labels, derive the display from `componentsApi.relations(id)` (filtered to the `providesAPI`/`consumesAPI` predicates) and render each as a link to `/apis/{id}`.
- **BREAKING (internal only)**: rebuild `TeamDetailPage` on the shared `EntityDetailPage` component — breadcrumb, header, tab bar (Overview/Members/Systems/Components/Resources/APIs), and right rail — replacing the current two-column layout with stacked, spacing-separated owned-entity sections. Retires the page's bespoke `OwnedTable` in favor of the same shared, properly-wired child table used elsewhere. This supersedes the current `catalog-web-ui` "Teams (Groups) pages" requirement, which specifies that exact two-column/stacked layout as intentional.
- Extend the `System`/`Component`/`Resource`/`API` entity response (`SystemSpecOut`/`ComponentSpecOut`/`ResourceSpecOut`/`ApiSpecOut`) with `ownerId`/`systemId`, sourced from the same owner/system FK objects already resolved to build the existing ref strings. Make each detail page's right-rail Owner field (and System field, where present) a link to that entity's detail page, reusing `RelationTargetLink`.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `catalog-web-ui`: "Teams (Groups) pages" requirement rewritten — Team detail page moves from the two-column/stacked-sections layout to the shared `EntityDetailPage` tabbed layout (Overview/Members/Systems/Components/Resources/APIs tabs), same chrome as System/Component/Resource/API. "Entity detail pages" requirement extended to describe Team's tab set alongside the other four kinds. New requirement covering double-click-to-navigate on related-entity tables within detail pages (Resources/Components/APIs tabs, Team's owned-entity tabs) and on Relations tab rows. New requirement covering Component's Provides/Consumes API links. New requirement covering rail Owner/System field navigation on System/Component/Resource/API detail pages.
- `entity-relations`: "Relations endpoint lists both directions" requirement extended — each relation entry additionally carries `targetKind`/`targetId` identifying the target entity, not just its `ref` string.
- `entity-catalog` (implementation detail, no formal spec delta in this change — see Note below): System/Component/Resource/API responses additionally carry `ownerId` (and `systemId`, where the kind has a `system` field) identifying the owner/system by id, not just their ref strings.

> **Note**: the `entity-catalog` field addition doesn't have its own spec delta here — this change doesn't otherwise touch that capability, and a bare-minimum-diff `/opsx:continue` pass would be needed to add one. The `catalog-web-ui` requirement below fully specifies the user-facing behavior this backend change enables.

## Impact

- **Backend**: `apps/catalog/api/views.py` (`RelationOut`, `_relations_out`) — add `targetKind`/`targetId` fields sourced from the already-resolved target object in `apps/catalog/relations.py`'s `entity_relations()`. `apps/catalog/api/schemas.py`/`views.py` (`SystemSpecOut`/`ComponentSpecOut`/`ResourceSpecOut`/`ApiSpecOut`) — add `ownerId`/`systemId` sourced from the already-resolved `instance.owner`/`instance.system` FK objects.
- **Frontend**:
  - `lib/useEntityRowActivation.ts` — reused as-is, wired into two more call sites.
  - `pages/SystemDetailPage.tsx` (`ChildTable`) — add row-click navigation.
  - `pages/TeamDetailPage.tsx` — rebuilt on `EntityDetailPage`; `OwnedTable` retired in favor of the shared child table.
  - `components/RelationsTab.tsx` — target column becomes a link using `targetKind`/`targetId`.
  - `pages/ComponentDetailPage.tsx` (`RefList`) — Provides/Consumes API sections redriven off relations data with links, instead of bare ref labels.
  - `lib/entities.ts` or a new small helper — kind→path map (`System→/systems`, `Component→/components`, `Resource→/resources`, `API→/apis`, `Group→/teams`) for building routes from `targetKind`.
  - `lib/types.ts` — `ownerId`/`systemId` added to the relevant `*Spec` interfaces.
  - `lib/railFields.tsx` — Owner/System fields render via `RelationTargetLink` instead of plain `refName(...)` text.
- **Out of scope**: User entities (no detail route exists, so Group member refs stay plain labels); Owner/System ref labels on list-page columns and Component's `dependsOn` are not made clickable in this change.
