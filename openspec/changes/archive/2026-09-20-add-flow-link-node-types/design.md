## Context

Flow steps (`plugins/flows/backend/atlas_plugin_flows/models.py`, `core/frontend/src/lib/types.ts`'s `FlowStep`) already split into two families:

- **Ref-backed** (`entity_ref`, `query_ref`, `event_ref`): the step never carries its own `title`/`summary` — the node's card always renders text resolved live from the reference's target, and a stale/removed-target warning indicator is available (`FlowRefWarning.tsx`).
- **Freeform** (`external_label`, plain `step`): the step carries its own `title`/`summary`, typed by the author in `FlowStepModal`.

A step may carry at most one of `entity_ref` / `external_label` / `query_ref` / `event_ref` (enforced identically in `models.py`'s `_validate_step_shape` and `flowSteps.ts`). The 10-kind "Add Step" picker (`FlowStepModal.tsx`'s `KIND_TILES`) is a fixed 2-column CSS grid, currently exactly filled (5 rows), with an explicit rule that no two horizontally/vertically adjacent tiles share an identity color.

`Flow` itself is a plain Django model with an integer `id` and, unlike the six entity-backed ref kinds, explicitly has no `kind:name` catalog ref namespace (documented in `models.py`) — so a "link to another Flow" reference cannot reuse the existing `entity_ref` + `resolve_ref()` machinery as-is.

The read-only detail-page canvas (`FlowGraph.tsx`) already has an unused `onBlockClick` hook, and already disables `nodesDraggable`/`nodesConnectable` but not `elementsSelectable` — a pointer-down-and-drag starting on a node currently falls through to canvas panning rather than doing nothing.

## Goals / Non-Goals

**Goals:**
- Let a Flow step reference another Flow (`flow_ref`) and let a Flow step reference an arbitrary external URL (`link_url`), each rendering as its own node kind.
- Let a viewer navigate from either node, in read-only view only, to the target — in a new tab — without that click being swallowed by, or confused with, canvas panning.
- Keep the picker grid evenly filled (12 tiles) with a palette that respects the existing adjacent-color rule.

**Non-Goals:**
- No sub-flow embedding/inlining — a Flow node is a hyperlink to another Flow's own diagram, not a transclusion of its steps. Cycles between Flows (A links to B, B links to A) are therefore not a data-integrity concern and need no cycle detection, unlike the existing `next_step`/`next_steps` transition graph *within* one Flow, which is already validated acyclic.
- No "Note"/annotation node type and no "Decision" node type — explicitly deferred; a decision point is already representable as a custom-colored/iconed plain `step`.
- No change to the existing `entity_ref`/`query_ref`/`event_ref` families' behavior.

## Decisions

**1. `flow_ref` is a new field, not an `entity_ref` string.** Since `Flow` has no `kind:name` ref namespace, `flow_ref` is a plain integer Flow id, resolved by a Flow existence/lookup query rather than `resolve_ref()`. It joins the existing mutual-exclusivity set: a step carries at most one of `entity_ref` / `external_label` / `query_ref` / `event_ref` / `flow_ref` / `link_url`.

**2. Flow is ref-backed; Link is freeform.** Flow joins the entity-backed family: no author-editable `title`/`summary` — the card always shows the target Flow's live `name` (title) and `description` (subtitle), the same rule already enforced for `entity_ref` steps (`models.py`, `FlowStepModal.tsx`'s `refBackedKind`). Link joins the freeform family alongside `external`/`step`: its own optional `title`/`summary`, reusing the existing generic fields rather than adding a dedicated label field. When `title` is blank, the card falls back to the `link_url` itself — not `step.id`, which is an opaque auto-generated counter (`step-4`, via `nextFlowStepId()`) carrying no information for a viewer. The URL itself is always shown as the card's subtitle (mirroring how `external`'s `external_label` is always shown as its subtitle), so the card never renders with zero informative content even when no title was authored.

**3. Icons: `BranchesRight` for Flow, `Link` for Link.** Flow reuses the exact icon already used for the "Flows" sidebar nav item (`navItems.ts`), for pre-existing user recognition. Link uses the plain chain glyph (`Link`) rather than `CircleLink`: every other kind's chip icon (Person, Persons, Cube, Database, PlugConnection, Layers, Compass, Magnifier, Thunderbolt, Flag) is an unframed flat glyph, and `CircleLink`'s circular framing would be the only chip breaking that visual consistency. `Link`'s chain shape is also unambiguous against the navigate button's `ArrowUpRightFromSquare` (arrow-out-of-box) glyph on the same card.

**4. The navigate action is a dedicated button, not a whole-card click, and view-only.** It renders in `NodeCard`'s existing chip row (alongside the label chip, `StaleRefWarning`, `RefreshRefButton`), following the codebase's established pattern that point actions are small dedicated overlay controls (`NodeDeleteButton`, `NodeAddNextButton`, `RefreshRefButton`) rather than whole-card gestures — clicking a node's body already means "select it" (`elementsSelectable` is not disabled in `FlowGraph.tsx`) and, on the editable canvas, "open its edit modal." The button renders only on the read-only detail-page canvas; the editable canvas (`FlowCanvasEditor.tsx`) never renders it, mirroring how `onRefresh` is the inverse case (edit-only, never on the read-only canvas).

**5. Navigation uses a real anchor element, not `onClick` + `window.open`.** The button is `target="_blank" rel="noopener noreferrer"` — an internal `react-router` `Link` to `/flows/:id` for a Flow node, a plain `<a>` to `link_url` for a Link node. This gets native middle-click / Cmd-or-Ctrl-click / right-click "open in new tab" behavior for free and avoids popup-blocker interference that a programmatic `window.open()` risks.

**6. The button needs both `nodrag` and `nopan`, not `nodrag` alone.** `nodrag` (already used by `NodeDeleteButton`/`NodeAddNextButton`/`RefreshRefButton`) only suppresses node-drag initiation. On the read-only canvas, `nodesDraggable` is already `false`, so a pointer-down-and-drag starting on a node currently falls through to canvas panning instead — `nopan` (already used on interactive edge elements in `FlowEdges.tsx`) is required in addition, so that starting a pan gesture from the button never fires navigation, and so a pan gesture is never misread as a click.

**7. `link_url` is validated as a well-formed absolute `http`/`https` URL on save**, on both backend (`models.py`) and frontend (`flowSteps.ts`), rejecting other schemes (e.g. `javascript:`) the same way other step fields are rejected on save — this is an author-supplied value that later renders as a clickable link, so unrestricted schemes are not just a UX foot-gun but an injection surface.

**8. A Flow node whose `flow_ref` no longer resolves reuses `StaleRefWarning`/`refStatus`.** Live status for `flow_ref` (target Flow's current `name`/`description`, and whether it still resolves) is surfaced on read the same way `entity_ref`/`query_ref`/`event_ref` live status already is. When the target no longer resolves, the node shows the existing warning-indicator treatment and the navigate button is disabled rather than linking to a dead page.

**9. New capability `flow-node-linking` for the data-model side**, mirroring the existing `flow-query-event-steps` split: the JSON grammar, save-time validation, and live-status surfacing for `flow_ref`/`link_url` get their own capability spec, while the UI-facing requirements (picker tiles, lookup widget, card rendering, navigate button, stale indicator) land as deltas on the existing `flow-management`/`visual-flow-editor` capabilities — the same split already used for Call/Event steps.

## Risks / Trade-offs

- **[Risk]** A Flow node might be read by users as "this flow is embedded here" rather than "this is a link elsewhere." → Mitigation: title/subtitle are drawn from the target Flow's own name/description (not e.g. "View Flow"), and the outbound-link icon on the navigate button signals "leaves this diagram," matching the same affordance already used elsewhere in the app for external links.
- **[Risk]** Picker grid color placement: the palette's existing adjacency rule (no two same-colored tiles touching, `FlowStepModal.tsx`'s `KIND_TILES` ordering) must be re-verified once Flow/Link are inserted, since inserting two tiles can change which tiles end up adjacent. → Mitigation: tasks.md calls out re-deriving tile order/colors as an explicit step, not an incidental one.
- **[Risk]** `flow_ref` currently has no restriction to the viewer's own System; a Flow node could reference a Flow in an entirely different System/team. → Not resolved here; see Open Questions.

## Open Questions

- Should `flow_ref` be restricted to Flows within the same home System as the authoring Flow, or is cross-System linking intentional (Flows are browsed/searched globally today, unscoped by the viewer's current System)?
- Does read access to a Flow via a `flow_ref` navigation need to respect any Flow-level read permission beyond what already gates the Flows list/detail routes, or is Flow read access already uniform for any signed-in user? (`flows-plugin`'s existing permission requirement only mentions writes being ownership-scoped.)
