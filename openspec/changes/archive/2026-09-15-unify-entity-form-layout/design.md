## Context

Today there are two independent implementations of an Add/Edit form:

- `EntityFormShell` (`core/frontend/src/components/EntityFormShell.tsx`), consumed by `SystemFormPage`, `ComponentFormPage`, `ResourceFormPage`, `ApiFormPage`. Single `<div style={{maxWidth: 560}}>`, fields stacked vertically (Name/Title/Description/Tags/`specFields` slot/Documentation), Save+Cancel as the last row inside the `<form>`.
- `FlowFormPage` (`plugins/flows/frontend/src/pages/FlowFormPage.tsx`), entirely bespoke. Save+Cancel directly under the title, then a `TabProvider` with General (fields left in a `flex: '0 0 300px'` column, Documentation right in `flex: '1 1 100%'`, no width cap) and Flow (the canvas) tabs.

Both `EntityDetailShell` (`core/frontend/src/components/EntityDetailShell.tsx:187-224`) and `FlowDetailPage` (`plugins/flows/frontend/src/pages/FlowDetailPage.tsx:64-82`) already share one header pattern for their action buttons: a flex row (`justifyContent: 'space-between', alignItems: 'flex-start'`) with the title/description on the left and the action buttons (Edit/Remove/Revive/Purge) on the right. This change makes the Add/Edit forms use that same pattern for Save/Cancel instead of inventing a third position.

## Goals / Non-Goals

**Goals:**
- One header action-row pattern for Save/Cancel, shared by all five Add/Edit forms, matching the existing detail-page header pattern.
- Component and API forms split into Overview (fields) / Documentation tabs, with Documentation no longer capped at 560px.
- No change to System's or Resource's structure beyond picking up the new header (still single column, still 560px-capped Documentation).
- No change to Flow's General/Flow tab structure, field layout, or canvas behavior — only where its Save/Cancel row sits.

**Non-Goals:**
- Not touching System/Resource Documentation width — explicitly deferred.
- Not adding tabs to System/Resource forms.
- Not touching Teams — no Add/Edit form exists for Groups (`editable={false}`).
- Not renaming or restructuring detail-page tabs (e.g. `EntityDetailShell`'s "Overview" tab, which shows documentation on the *read* side) to match the new form-side tab names. The naming overlap between form-side "Overview" (fields) and detail-side "Overview" (documentation) is a known asymmetry this change does not resolve — see Open Questions.
- Not changing backend contracts, validation rules, or field sets — this is a layout/structure change only.

## Decisions

### 1. Extract the shared header action-row layout, don't re-duplicate it a third and fourth time
It already exists twice (`EntityDetailShell`, `FlowDetailPage`) as the same inline flex styles. Rather than copy those styles into `EntityFormShell` and `FlowFormPage` as a third and fourth copy, pull the row (title-left / actions-right flex container) into one small shared piece in `core/frontend/src/components` that all four call sites use.
- **Alternative considered**: leave it as inline duplicated styles in each of the four places. Rejected — four independent copies of the same flex rule is exactly the kind of drift that produced this proposal in the first place (Flow's version already diverged once).
- Keep it minimal: a layout container, not a component that also knows about buttons/titles/forms — it just places two children (left content, right content) the way the detail shells already do.

### 2. `EntityFormShell` gains an opt-in tabbed layout, rather than Component/API growing bespoke Flow-style form pages
`EntityFormShell` keeps its existing props (`metadata`, `onMetadataChange`, `specFields`, `onSubmit`, `cancelTo`) unchanged. It gains a layout switch (e.g. `layout: 'single' | 'tabbed'`, default `'single'`) so:
- `SystemFormPage`/`ResourceFormPage` pass nothing and keep today's single-column body, just under the new header.
- `ComponentFormPage`/`ApiFormPage` pass `layout="tabbed"`; `EntityFormShell` internally renders `TabProvider`/`TabList`/`TabPanel` with an **Overview** tab (Name/Title/Description/Tags + the same `specFields` slot, still width-capped) and a **Documentation** tab (just the Markdown editor, no width cap).
- **Alternative considered**: give Component/API their own bespoke form pages built the way `FlowFormPage` is, each hand-rolling the header + `TabProvider`. Rejected — the only thing that differs between Component's and API's "tabbed" needs is their `specFields` content, which is already exactly what the `specFields` slot exists for. Four near-duplicate hand-rolled tab implementations is worse than one shared branch inside the shell that already owns this responsibility.
- Flow is **not** migrated onto `EntityFormShell` in this change — its General tab's two-column (fields+doc side by side) shape is structurally different from the Overview/Documentation split, and folding it in would be a bigger, riskier change than what was scoped here. `FlowFormPage` keeps its own component, just adopts the shared header piece from Decision 1.

### 3. Header buttons stay inside the same `<form>` element
Save/Cancel move visually, but keep the same submission mechanics: the header row renders inside the same `<form onSubmit=...>` that wraps the tab content, so the Save button stays `type="submit"` (no imperative submit-by-ref needed) and Enter-to-submit from a text field keeps working. This mirrors what `FlowFormPage` already does today for its top button row — only the row's position within the header changes.

### 4. Name-field validation must switch tabs on Component/API too
`EntityFormShell`'s existing `nameTouched`/`nameInvalid` state assumes the Name field is always on-screen. Once Component/API can hide it behind a Documentation tab, `handleSubmit` must switch `activeTab` back to `'overview'` when Name is empty, the same way `FlowFormPage.handleSubmit` already switches back to `'general'` today (`FlowFormPage.tsx:314-319`). This is existing precedent, not a new pattern — just needs applying inside `EntityFormShell`'s tabbed branch too.

### 5. Tab naming: "Overview" / "Documentation" for Component and API, not "General"
Flow's tab is called "General" because it mixes fields *and* documentation together in one tab. Component/API's fields-only tab is a different shape (documentation is fully separated out), so it gets a different name — "Overview" — to avoid implying the Flow-style combined layout. The documentation tab is named "Documentation" (not reusing "Overview", which already means "documentation preview" on the read-side detail pages — see Non-Goals).

## Risks / Trade-offs

- **[Risk]** Existing tests assert current button position/order/DOM structure (`EntityFormShell.test.tsx`, `FlowFormPage.test.tsx`, and consuming pages' tests) → **Mitigation**: update them alongside the implementation as part of this change's tasks; no separate migration needed since these are UI-only assertions, not stored data or API contracts.
- **[Risk]** A user with the Documentation tab open on Component/API, who submits with an empty Name, needs to see the tab switch back to Overview (Decision 4) or the inline error is invisible → **Mitigation**: reuse Flow's proven `setActiveTab` guard in `handleSubmit`.
- **[Trade-off]** `EntityFormShell` picks up a second layout mode instead of staying single-purpose → accepted, since the alternative (Decision 2) duplicates tab machinery four times for no behavioral difference beyond field content.

## Open Questions

- Should the detail-side "Overview" tab (documentation) eventually be renamed for symmetry with the form-side "Overview" (fields) now that they mean different things? Left as a follow-up, not decided here (see Non-Goals).
