## Why

Add/Edit forms for System, Component, Resource, API, and Flow currently disagree on where Save/Cancel live and how content is laid out. Four of the five (System/Component/Resource/API, via the shared `EntityFormShell`) put Save/Cancel at the bottom of a single stacked column and cap the whole form — including the Markdown Documentation editor — to ~560px wide. Flow has its own bespoke form with Save/Cancel under the title, a General/Flow tab split, and a Documentation editor that stretches full-width because it was never wrapped in that 560px cap. None of this was a deliberate difference; it's just where each form ended up. It also means every entity's Add/Edit form looks structurally different from that same entity's own read-only detail page, which already puts its actions (Edit/Remove/Revive/Purge) top-right next to the title.

## What Changes

- Move Save/Cancel on every Add/Edit form (System, Component, Resource, API, Flow) into a single shared top-right header row — title left, actions right — reusing the header layout already used by `EntityDetailShell` and `FlowDetailPage` for their action buttons. Button order is unchanged (primary action left, Cancel right); only position moves.
- **BREAKING (UI only, no API/data change)**: Remove the bottom-of-form Save/Cancel row from `EntityFormShell` and the under-title Save/Cancel row from `FlowFormPage`. Anyone relying on the current button position (e.g. existing UI tests asserting layout) will need updating.
- Split Component's and API's Add/Edit forms into two tabs — Overview (Name/Title/Description/Tags and kind-specific spec fields) and Documentation (the Markdown editor alone, full width, no longer capped at 560px).
- Leave System's and Resource's Add/Edit forms as a single, un-tabbed column (their field count doesn't justify a second tab); their Documentation editor's width is intentionally left as-is in this change.
- Leave Flow's form structure otherwise unchanged: still General/Flow tabs, General tab still lays fields and Documentation side-by-side full-width; only the button row moves into the new shared header.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `catalog-web-ui`: the "Add/Edit forms for manual entities only" requirement changes — Save/Cancel move to a shared top-right header row instead of following the fields, and the Documentation editor's position/width for Component and API forms changes (own tab, full width) instead of always following the fields in one column.
- `flow-management`: the Flow create/edit form's Save/Cancel position changes from under the title to the same shared top-right header row; the General/Flow tab structure itself is unchanged.

## Impact

- `core/frontend/src/components/EntityFormShell.tsx` — shared shell used by System/Component/Resource/API forms: header/button layout rework, and a new tabbed-content path for consumers that opt into the Overview/Documentation split.
- `core/frontend/src/components/EntityDetailShell.tsx` — read for reference only (its header action-row layout is being replicated, not modified).
- `plugins/standard-catalog/frontend/src/pages/ComponentFormPage.tsx`, `plugins/apis/frontend/src/pages/ApiFormPage.tsx` — opt into the new Overview/Documentation tab split.
- `plugins/standard-catalog/frontend/src/pages/SystemFormPage.tsx`, `plugins/standard-catalog/frontend/src/pages/ResourceFormPage.tsx` — keep single-column body, just pick up the new header button position via `EntityFormShell`.
- `plugins/flows/frontend/src/pages/FlowFormPage.tsx` — button row removed from under the title and rebuilt in the shared top-right header style; General/Flow `TabProvider` unchanged.
- Existing tests that assert current button placement/order (`EntityFormShell.test.tsx`, `FlowFormPage.test.tsx`, and the per-entity form page tests) will need updating to match the new layout.
- Teams: no create/edit form exists (`TeamDetailPage` is `editable={false}`, ingested-only) — out of scope, untouched.
