## 1. Shared header action-row

- [x] 1.1 Extract the title-left/actions-right flex header row (currently duplicated inline in `EntityDetailShell.tsx:187-224` and `FlowDetailPage.tsx:64-82`) into one small shared layout piece in `core/frontend/src/components`.
- [x] 1.2 Update `EntityDetailShell` and `FlowDetailPage` to use the extracted piece instead of their own inline styles, with no visible change to either.

## 2. `EntityFormShell`: header buttons + tabbed layout

- [x] 2.1 Move `EntityFormShell`'s Save/Cancel row out of the bottom of the form and into the shared header row from Task 1.1 (title left, buttons right), keeping the buttons inside the existing `<form>` element and `type="submit"` on Save.
- [x] 2.2 Add a `layout: 'single' | 'tabbed'` prop to `EntityFormShell` (default `'single'`); single-column behavior for existing callers must be unchanged aside from the header move.
- [x] 2.3 Implement the `'tabbed'` branch: `TabProvider`/`TabList`/`TabPanel` with an "Overview" tab (Name/Title/Description/Tags + the `specFields` slot, same width cap as today) and a "Documentation" tab (the `DocumentationEditor` alone, no width cap).
- [x] 2.4 In the tabbed branch's submit handler, switch `activeTab` back to `'overview'` when Name is empty on submit, mirroring `FlowFormPage.tsx:314-319`, so the inline validation error is visible.
- [x] 2.5 Update `EntityFormShell.test.tsx` for the new header position and to cover both `layout` modes.

## 3. Component and API forms adopt the tabbed layout

- [x] 3.1 `ComponentFormPage.tsx`: pass `layout="tabbed"` to `EntityFormShell`.
- [x] 3.2 `ApiFormPage.tsx`: pass `layout="tabbed"` to `EntityFormShell`, keeping its conditional spec-source block (inline text / URL / file upload) inside the Overview tab's `specFields` slot.
- [x] 3.3 Manually verify both forms: Overview tab holds all fields at today's width, Documentation tab renders full-width, Save/Cancel work from either tab.

## 4. System and Resource forms keep single-column

- [x] 4.1 Confirm `SystemFormPage.tsx` and `ResourceFormPage.tsx` need no prop changes (default `layout="single"`) and only pick up the new header position via `EntityFormShell`.
- [x] 4.2 Manually verify both forms: single column unchanged, Documentation editor still after the fields at today's width, Save/Cancel now top-right.

## 5. Flow form adopts the shared header

- [x] 5.1 Remove `FlowFormPage`'s current under-title Save/Cancel row (`FlowFormPage.tsx:360-367`).
- [x] 5.2 Render Save/Cancel using the shared header piece from Task 1.1, above the `TabProvider`, inside the same `<form>`; keep button order and `loading`/`disabled` behavior unchanged.
- [x] 5.3 Confirm the General tab's fields-left/Documentation-right layout and the Flow tab's canvas/toolbar are otherwise untouched — no Save/Cancel added to the Steps toolbar.
- [x] 5.4 Update `FlowFormPage.test.tsx` for the new header position.

## 6. Cleanup and verification

- [x] 6.1 Run the frontend test suite for `core/frontend` and the `apis`, `standard-catalog`, and `flows` plugin frontends.
- [x] 6.2 Manually walk through create and edit for each of System, Component, Resource, API, and Flow, confirming header actions, tab structure, and Documentation width match the spec deltas.
- [x] 6.3 Confirm Teams remains untouched (`TeamDetailPage` still `editable={false}`, no form added).
