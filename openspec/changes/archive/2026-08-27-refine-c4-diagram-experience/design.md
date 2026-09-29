## Context

`add-c4-architecture-diagrams` introduced a System Context endpoint and a Component Diagram endpoint. The former deliberately maps Component, API, and Resource endpoints to their containing Systems. The System detail page calls the context view simply “C4 Diagram”, so a user expecting internal architecture sees only the correct but differently scoped Context view. The renderer currently sets a global left-to-right layout and retains only labels and technology on relationship payloads, leaving authored interaction kinds and catalog element roles visually indistinguishable. The relationship editor accepts an arbitrary text ref although the catalog already exposes searchable reference controls.

## Goals / Non-Goals

**Goals:**

- Preserve the System Context as a System-level diagram and add a separately named System Architecture view for a selected System's internals.
- Give all Atlas C4 diagrams a deterministic top-down layout and an Atlas-owned visual vocabulary based on element roles and interaction kinds.
- Make User and Group actor references available through Architecture Relationship authoring and demonstrate an actor interaction in the booking demo.
- Replace raw Target ref entry with validated, searchable catalog selection.

**Non-Goals:**

- Implement generic user-configurable PlantUML themes, per-entity arbitrary colours, a graph editor, or a new Actor database model.
- Change ownership relations into runtime interactions, or include components/resources in System Context diagrams.
- Add a remote rendering service, image caching, or extra C4 diagram families beyond the System Architecture view.

## Decisions

### 1. Add a System Architecture view rather than expanding System Context

`GET /api/diagrams/system/{id}/?view=architecture` will produce a ComponentDiagram-style scope containing the selected System's Components plus its APIs and Resources. Explicit and derived relationships between visible elements follow the same explicit-precedence rule as Component diagrams. The System page presents distinct “System Context” and “System Architecture” tabs. This retains C4 abstraction boundaries; adding internals to Context would make both diagrams harder to read.

### 2. Map catalog roles and interaction kinds to a closed set of PlantUML tags

Every emitted element receives Atlas role tags: selected component, internal component, database, queue, generic resource/API, external endpoint, and Person. Explicit Architecture Relationships receive a tag derived from `interaction_kind`; derived edges receive `Derived`. `diagram_payload` supplies `LAYOUT_TOP_DOWN`, a visible legend, and fixed tag definitions for those names. Catalog free-form tags remain metadata, not styling input, so output is stable and safe. The style set mirrors the structure of the referenced `c4-diagrams` JSON examples while using Atlas’s own semantic names and palette.

### 3. Reuse the reference lookup for polymorphic architecture targets

The relationship form will use a single target selector backed by the catalog reference search/list machinery. It filters to relationship-supported target kinds (System, Component, API, Resource, User, Group), renders kind plus display name, and submits the canonical ref. The backend remains authoritative for ref validity and permissions. Source selection stays implicit: the current detail entity is the outgoing source.

### 4. Seed explicit actor interactions as normal manual-origin relationships

The booking demo will create a representative User catalog entity if needed and an outgoing actor relationship to a System or Component. The existing renderer maps only explicitly related User/Group entities to `Person`; no ownership inference is added. The seed stays idempotent and covers all interaction kinds and an external relationship.

## Risks / Trade-offs

- [System Architecture can be crowded] → scope it to one System and use the interactive viewer; do not include every cross-system element except directly related externals.
- [Style tags can obscure diagram meaning] → keep a closed tag vocabulary and show a legend with role/interaction descriptions.
- [A polymorphic lookup can show too many records] → filter by supported kinds and provide search with type labels.
- [New endpoint/view can break existing URL assumptions] → retain `system/context` unchanged and add validation/tests for the new `system/architecture` pair.

## Migration Plan

1. Add builders, endpoint validation, styles, and test coverage while retaining current Context and Component URLs.
2. Deploy the UI tabs and target lookup together with backend support.
3. Seed demo relationships on explicit invocation; no database migration is needed.
4. Roll back by hiding the new UI tab; existing relationship rows and the Context endpoint are unaffected.

## Open Questions

- None blocking: System Architecture uses top-down layout and the System Context remains a separate, named tab.

## Verification Notes

Manual verification against locally rendered PlantUML SVGs (task 4.1/4.2) surfaced two implementation defects, both fixed in place without changing the decisions above:

- `diagram_payload` set PlantUML's `layout_with_legend` render option, which emits the library's hardcoded 4-row legend (`person`/`system`/`external person`/`external system`) regardless of any custom tags. The Atlas role and interaction-kind entries from Decision 2 never appeared. Fixed by switching to the `show_legend` render option, which emits `SHOW_LEGEND()` and renders the dynamic, tag-aware legend that reflects `AddElementTag`/`AddRelTag` entries actually used in the diagram.
- `_component_element` (used by both `build_component_diagram` and `build_system_architecture`) did not special-case User/Group entities, so an explicit actor endpoint rendered as a plain `Component` box instead of `Person`/`PersonExt` — contradicting Decision 4's "renderer maps only explicitly related User/Group entities to `Person`". Fixed by routing actor-kind entities to `Person`/`PersonExt` with the `AtlasPerson` tag, matching the System Context path's existing behavior.

Regression tests were added in `test_c4.py` for both fixes; the full backend suite (121 tests) and frontend suite (32 tests, typecheck, lint, build) pass.
