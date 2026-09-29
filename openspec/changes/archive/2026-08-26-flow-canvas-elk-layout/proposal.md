## Why

The Flow diagram (`FlowGraph.tsx`) currently renders every transition as an unlabeled grey line between unstyled grey blocks, even though each transition already carries an optional `label` that goes unrendered. The reference `@gravity-ui/graph` playground (vendored at `temp/landing/src/components/GraphPlayground`) shows what the same library can look like with connection labels and a real color palette turned on, and also ships an ELK-based auto-layout integration that produces cleaner left-to-right tree layouts than the hand-written pass this app currently uses. None of this requires touching how Flows are authored or stored — it's a rendering upgrade to an existing, already-shipped view.

## What Changes

- Turn on connection-label rendering (`showConnectionLabels: true`) so a transition's `label` (from `next_step.label` / a `next_steps[]` entry's `label`) is drawn on its connection line. The data already flows into `flowLayout.ts`'s output; only rendering was missing.
- Replace `flowLayout.ts`'s hand-written two-pass tree layout with `@gravity-ui/graph`'s bundled ELK integration (`elk.direction: RIGHT`), adding `elkjs` as a new frontend dependency. **BREAKING (internal only)**: this reverses `add-flows/design.md` Decision 5's explicit "no dagre/elk dependency" non-goal — noted here since that was a deliberate prior decision, not an oversight. Layout becomes asynchronous (ELK's `useElk` hook returns a Promise-backed result), so the live-preview re-render on every JSON keystroke needs debouncing and must hold the last-good layout on screen while a new one resolves, to preserve the existing "live preview... without requiring a save" behavior.
- Apply a fixed, uniform visual palette to blocks, connections, anchors, and the canvas background, ported from the reference playground's `viewConfiguration.colors` recipe. This is a single fixed look, not a data-driven style (no coloring by entity kind or step type) and not a new user-facing setting.
- The canvas remains a pure, non-draggable, non-connectable view computed entirely from `steps[]` — no change to how Flows are authored, no new fields on `FlowStep`, no backend or API change. (Full-canvas editing — drag-to-reposition, draw-to-connect — was explored and explicitly rejected for this change: it would require persisting `x`/`y` per step, duplicating the server's strict-tree validation client-side for connection-drawing UX, and an Apply-gated JSON→canvas sync that conflicts with the locked "live preview... without requiring a save" spec scenario.)

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `flow-management`: the step-diagram rendering requirement gains a scenario for transition labels appearing on connections; the existing "left-to-right tree diagram" language is satisfied by ELK's `RIGHT` direction and does not otherwise change (layout engine choice and color palette are implementation detail, not spec-visible behavior beyond the label addition).

## Impact

- `frontend/src/lib/flowLayout.ts`: layout algorithm replaced (ELK instead of hand-written DFS/two-pass), return shape / call signature likely becomes async or hook-based.
- `frontend/src/components/FlowGraph.tsx`: `GRAPH_CONFIG` gains `showConnectionLabels: true` and a `viewConfiguration.colors` block; consumes the new async layout (loading/debounce handling).
- `frontend/src/index.css`: `.flow-graph__block` (and related connection/canvas rules) restyled from generic `--g-color-*` tokens to the fixed palette.
- `frontend/package.json`: new dependency, `elkjs`.
- No backend, API, or `steps` JSON schema changes. No change to `FlowFormPage.tsx`'s JSON-editor-is-source-of-truth model.
