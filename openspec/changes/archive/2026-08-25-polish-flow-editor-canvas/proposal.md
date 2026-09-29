## Why

The Flow editor (`FlowFormPage.tsx`) already renders a live `steps`-JSON-to-diagram preview, exactly as `flow-management`'s design intended ("mirroring `@gravity-ui/graph`'s own playground pattern," `add-flows/design.md` Decision 6) — but only the data flow was built, not the authoring surface. Today `steps` is edited in a plain monospace `<TextArea>` with no syntax highlighting, no validation feedback until save, and no way to add a step without hand-writing JSON; the diagram canvas has no zoom, pan-to-fit, or way to jump from a node back to its JSON. Comparing directly against Gravity UI's own graph playground (cloned locally at `temp/landing/src/components/GraphPlayground/Playground`, the reference the original design decision pointed at) makes the gap concrete: that playground ships a real JSON editor (Monaco, schema-validated) and a floating zoom/fit toolbar, both absent from Atlas today.

## What Changes

- Replace `FlowFormPage.tsx`'s raw `<TextArea>` for `steps` with a Monaco-based JSON editor (`@monaco-editor/react`, a new dependency), schema-validated against the `FlowStep[]` shape, themed to match Atlas's existing `.g-root_theme_light`/`.g-root_theme_dark` tokens. The existing live re-parse-on-change wiring is preserved as-is — no staging/"Apply" gate is introduced (see design.md for why not).
- Add a floating zoom-in / zoom-out / fit-to-viewport toolbar to `FlowGraph.tsx`. Because `FlowGraph` is shared between the edit page's preview pane and the read-only `FlowDetailPage`, both surfaces gain working zoom controls; `FlowDetailPage.tsx` itself is not modified.
- Add click-to-locate: clicking a step node on the canvas scrolls the JSON editor to and selects that step's JSON block. Wired only from `FlowFormPage` via a new optional `onBlockClick` prop on `FlowGraph`; `FlowDetailPage` does not pass it.
- Add an "Add Step" button to `FlowFormPage` that appends a new step object (fresh, non-colliding `id`) to the `steps` JSON and scrolls the editor to it. Disabled while the current JSON is invalid.
- Add a JSON-panel collapse/expand toggle to `FlowFormPage` so the diagram preview can take the full width while editing.

**Explicitly not changing:** no drag-to-reposition or drag-to-connect on the canvas (positions stay computed by `flowLayout.ts`, per `add-flows/design.md` Decision 5), no merge of the detail and edit pages, no backend/API changes, no change to the strict-tree or `entity_ref` validation rules, no graph-settings popover (connection style / arrow visibility).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `flow-management`: the "Flow detail page renders and edits the step diagram" requirement gains scenarios for a real code editor (syntax highlighting + schema validation surfaced inline, not just on save), zoom/fit-to-viewport controls, node-click-to-JSON navigation, in-editor step creation, and a collapsible editor pane. No existing scenario in this requirement is removed or weakened — the "live preview, no save required" behavior is explicitly preserved.

## Impact

- **Frontend dependency**: adds `@monaco-editor/react` to `frontend/package.json` (new, ~multi-MB, lazy-loadable bundle addition — see design.md for the tradeoff discussion).
- **Code**: `frontend/src/pages/FlowFormPage.tsx` (editor swap, Add Step, collapse toggle), `frontend/src/components/FlowGraph.tsx` (zoom toolbar, `onBlockClick` prop), `frontend/src/index.css` (`.flow-graph` positioning + toolbar styles), new `frontend/src/lib/flowStepSchema.ts` (JSON Schema) and `frontend/src/lib/monacoFlowTheme.ts` (light/dark theme defs).
- **Not touched**: `frontend/src/pages/FlowDetailPage.tsx`, backend (`apps/catalog`), API contracts, `flowLayout.ts`'s layout algorithm.
