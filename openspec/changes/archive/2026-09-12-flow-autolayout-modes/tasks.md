## 1. Backend: persisted mode fields

- [x] 1.1 In `plugins/flows/backend/atlas_plugin_flows/models.py`'s `Flow` model, add `autolayout_enabled` (boolean, default `True`) and `layout_direction` (choice of `LAYOUT_LEFT_RIGHT`/`LAYOUT_TOP_DOWN`, default `LAYOUT_LEFT_RIGHT`).
- [x] 1.2 Wire both fields through the Flow API (read and write) in `api/schemas.py` (or wherever the Flow serializer lives), so create/update/retrieve all round-trip them.
- [x] 1.3 Add/update backend tests in `plugins/flows/backend/atlas_plugin_flows/tests/test_flow_crud.py`: a Flow created without either field defaults to `autolayout_enabled=True`/`layout_direction=LAYOUT_LEFT_RIGHT`; both fields round-trip through create and update.

## 2. Frontend: mode-aware position resolution

- [x] 2.1 In `plugins/flows/frontend/src/lib/flowLayout.ts`, replace `mergeStepPositions`'s per-step "`position` wins if present" merge with mode-aware resolution: when autolayout is enabled, every step's position comes from a fresh `computeFlowAutolayout` call (no per-step override); when disabled, every step's position comes from its own stored `position` (falling back to `{0, 0}` only for a step that somehow has none), with no ELK call at all.
- [x] 2.2 Route `layout_direction` into `computeFlowAutolayout`/`alignFlowPositions` from the Flow's persisted field instead of `flowDiagramPreferences.ts`'s local preference.
- [x] 2.3 Remove `flowDiagramPreferences.ts` and its `useFlowDiagramPreferences` hook now that direction is a persisted Flow field, not a per-viewer one; update any remaining call sites.
- [x] 2.4 Add/update unit tests in `flowLayout.test.ts` for the new mode-aware resolution: autolayout-on always returns fresh ELK positions regardless of any stored `position`; autolayout-off always returns stored positions untouched, with `computeFlowAutolayout` never invoked.

## 3. Frontend: canvas editor wiring

- [x] 3.1 In `FlowCanvasEditor.tsx`, accept `autolayoutEnabled`/`layoutDirection` as props sourced from the Flow being edited (replacing local direction-preference state), and pass them into the layout effect and `handleAutoLayout`.
- [x] 3.2 Rework the passive layout `useEffect` (~line 194): while `autolayoutEnabled` is true, recompute the whole graph via ELK on every `steps` change and write the result back into every step's `position` via `onChange` (not just render it); while false, resolve positions per task 2.1 with no ELK call, and use the existing `nextConnectedPosition`/`resolveConnectedPosition`/`nextRowPosition` helpers only for placing a newly-added step.
- [x] 3.3 Resolve the drag-while-autolayout-on interaction (design.md Open Questions): either disable the node-drag gesture on the canvas while `autolayoutEnabled` is true, or leave it enabled and confirm the next recompute cleanly overwrites the dragged position with no jitter/loop. Implement whichever is chosen and note the decision in a code comment.
- [x] 3.4 Rename `handleAutoLayout`'s UI control (currently labeled "Auto layout") to a distinct label not shared with the new `autolayout_enabled` setting, and show/enable it only while `autolayoutEnabled` is false. Its behavior (recompute and persist every position once, without changing `autolayoutEnabled`) is otherwise unchanged.
- [x] 3.5 Add a UI control for toggling `autolayout_enabled` itself (exact placement is an implementation call per design.md's Open Questions — e.g. alongside the canvas toolbar or a Flow-level settings area).

## 4. Frontend: form wiring and persistence

- [x] 4.1 In `FlowFormPage.tsx`, add `autolayout_enabled`/`layout_direction` to the form's local state, seeded from the existing Flow when editing (defaulting to `true`/`LAYOUT_LEFT_RIGHT` for a new Flow).
- [x] 4.2 Include both fields in `handleSubmit`'s save payload (`input`).
- [x] 4.3 Verify (don't just assume) that the existing `Cancel` button (~line 324) already discards any in-session change to these two fields along with the rest of `steps`, since neither is written anywhere outside local component state before submit.

## 5. Seed data

- [x] 5.1 In `core/backend/server/apps/catalog/management/commands/seed_booking_demo.py`, confirm the demo Flows end up with `autolayout_enabled=True`/`layout_direction=LAYOUT_LEFT_RIGHT` (via model defaults, or set explicitly if the command constructs Flow rows with all fields spelled out today).
- [x] 5.2 Re-run `seed_booking_demo` against the dev database (no migration needed — see design.md's Migration Plan) and confirm the reconverging demo Flows (`search-flow`, `cancellation-flow`, `notification-delivery-flow`) still render correctly now that autolayout recomputes on every load.

## 6. Edge-routing spike (investigation only — see design.md Non-Goals)

- [x] 6.1 With autolayout guaranteed always-fresh (tasks 2-3 done), spike rendering `FlowEdges.tsx`'s `FlowTransitionEdge` from ELK's own `bendPoints` (available on `elk.layout()`'s result) instead of `getSmoothStepPath`, against the seeded reconverging demo Flows from task 5. This task's deliverable is a finding, not a required code change: record whether `bendPoints`-based rendering visibly fixes the "edge through an unrelated node" case without regressing plain (non-reconverging) edges, and whether it's worth adopting now or needs further work first. **Finding recorded in design.md's Risks section: not adoptable as-is — `alignSiblingColumns`'s post-ELK shift invalidates raw `bendPoints` on the exact reconverging shape (`cancellation-flow`) this was meant to fix; `getSmoothStepPath` stays as the renderer.**

## 7. Docs/comments cleanup

- [x] 7.1 Sweep comments describing the old per-step "`position` always wins if present" model (e.g. `flowLayout.ts`'s file header, `mergeStepPositions`'s doc comment, `FlowCanvasEditor.tsx`'s passive-effect comments) and update them to describe the new Flow-level binary mode.

## 8. Manual verification

- [x] 8.1 In the running app: with a Flow's autolayout on, add and delete steps and confirm every step's position recomputes and persists; drag a node and confirm the chosen task-3.3 behavior; toggle autolayout off, drag nodes freely, add a step and confirm it's placed without overlap and without invoking ELK; toggle autolayout back on and confirm a full recompute; confirm `Cancel` discards an in-progress toggle change without saving it. **Verified against `search-flow` in the running app: add/delete steps trigger a full ELK recompute while autolayout is on; toggling off shows the "Tidy layout" control and a manually-added step is placed by `nextRowPosition` with no ELK call (existing nodes stay put); toggling back on triggers a full recompute; Cancel discarded an in-session toggle-off, confirmed by reopening Edit and seeing autolayout still `true`. Node-drag itself couldn't be driven through the browser-automation harness (it registered as a canvas pan, not a node drag) — verified by code inspection instead: `handleNodeDragStop` always writes the dragged position, and the passive effect overwrites it on the next recompute while autolayout is on, matching the chosen task-3.3 behavior.**
- [x] 8.2 Confirm `layout_direction` renders identically for two different viewers (e.g. two browser profiles) regardless of either one's local browser state, now that it's a persisted Flow field rather than `localStorage`. **Verified: poisoned the legacy `atlas.flow-diagram-preferences.v1` localStorage key to `LAYOUT_TOP_DOWN` (a leftover from before this change) and confirmed the read-only Flow diagram still rendered `LAYOUT_LEFT_RIGHT` (the server value) — proving direction no longer reads from localStorage at all. This surfaced a real bug along the way (see design.md's Risks finding): the read-only view collapsed every node onto `{0, 0}` for any Flow without persisted per-step positions (i.e. every reseeded demo Flow), since it never computed autolayout itself. Fixed by making `FlowGraph`/`FlowGraphCanvas` mode-aware like the editor; verified against `search-flow` and `cancellation-flow` post-fix.**
