## Context

`flow-management` (from `add-flows`, status complete but not yet archived into `openspec/specs/`) already implements the data-flow half of its own design: `FlowFormPage.tsx` maintains `steps` as JSON text, re-parses it on every keystroke (`useMemo` over `parseSteps`), and feeds the result straight into `FlowGraph.tsx`, which renders it via `@gravity-ui/graph` using a hand-written tree layout (`flowLayout.ts`). `add-flows/design.md` Decision 6 explicitly chose this approach "mirroring `@gravity-ui/graph`'s own playground pattern." What was never built is the playground's authoring *surface* — the plain `<TextArea>` has no highlighting, no inline validation, and the canvas (`FlowGraph.tsx`) exposes no zoom/pan controls beyond a one-time auto-fit on mount (`zoomTo('center', {padding: 80})` in `GraphState.ATTACHED`).

The actual Gravity UI graph playground source is available locally at `temp/landing/src/components/GraphPlayground/Playground` (a clone of the public playground, not part of Atlas's own frontend — reference only, not a dependency). Reading it directly (rather than inferring from the rendered page) surfaced the real implementation choices:
- `Playground/Editor/index.tsx` + `schema.ts` + `theme.ts`: a Monaco editor (`@monaco-editor/react`) with a literal JSON Schema driving live validation/autocomplete, and a hand-defined `monaco.editor.defineTheme()` (Monaco cannot consume CSS custom properties, so its theme colors must be literal).
- `Playground/Toolbox.tsx`: a ~50-line floating zoom toolbar (`Button view="raised"` + `@gravity-ui/icons`) calling `graph.zoom({scale})` / `graph.zoomTo('center')`.
- `Playground/GraphPlayground.tsx`: wires `blocks-selection-change` → `editorRef.current.scrollTo(blockId)`, and an `editorOpened` state toggling the JSON pane's visibility.
- Critically, the original's `Apply` button only gates one direction of sync (typed JSON → canvas); canvas-driven changes (drag, add) flow into the JSON editor automatically, live, no gate. That asymmetry exists because the original supports live canvas editing (drag/connect) that Atlas's `flow-management` deliberately does not (`add-flows/design.md` Decision 5: layout is computed from the steps tree, not hand-placed).

Atlas's `flow-management` spec (`openspec/changes/add-flows/specs/flow-management/spec.md`) already has a locked scenario: "Live preview updates as the JSON is edited... without requiring a save." That constrains this change: whatever authoring surface is added must keep that behavior, not replace it with an Apply-gated one.

## Goals / Non-Goals

**Goals:**
- Give the `steps` JSON editor real authoring ergonomics: syntax highlighting, inline schema validation, and an "Add Step" affordance — while keeping edits live (no staging gate).
- Give the diagram canvas manual zoom in/out and fit-to-viewport controls, available everywhere `FlowGraph` is rendered (edit preview and read-only detail page alike).
- Let a canvas node be clicked to jump straight to its JSON, closing the loop between the two panes without needing drag-based canvas editing.

**Non-Goals:**
- No canvas-based editing of node position or connections (no `ECanDrag` change, no `canCreateNewConnections`). Node position stays fully computed by `flowLayout.ts`.
- No Apply/staging button — preserving the existing live-preview requirement takes priority over mirroring the original's UI 1:1.
- No graph-settings popover (bezier-vs-straight connections, arrow visibility) — decorative, not requested, and Atlas's connections aren't currently configurable at all.
- No merge of `FlowDetailPage` and `FlowFormPage` into a single page.
- No backend, API, or validation-rule changes. Schema validation added here is a client-side UX layer only; the server remains the source of truth for `entity_ref` resolution and the strict-tree rule.

## Decisions

**1. Editor library: Monaco (`@monaco-editor/react`), not CodeMirror.**
The original playground's real payoff isn't syntax coloring, it's the JSON-Schema-driven validation/autocomplete (`Editor/schema.ts`), which is a built-in Monaco capability (`monaco.languages.json.jsonDefaults.setDiagnosticsOptions`). Reimplementing equivalent schema-aware validation on top of CodeMirror would mean hand-rolling what Monaco gives for free. The cost is bundle size (Monaco is multi-MB); `@monaco-editor/react`'s default loader fetches it from a CDN-hosted worker setup lazily, so it doesn't block Atlas's initial app bundle — only the Flow edit route pays for it, on demand. Rejected: CodeMirror 6 — smaller, but would require writing and maintaining a custom JSON-Schema validator and error-surfacing UI to match what Monaco does natively.

**2. No Apply/staging gate — live sync stays live.**
The original gates JSON→canvas sync behind `Apply` because it also supports canvas→JSON live sync (drag a block, its JSON updates immediately) — the gate exists to stop a transiently-invalid typed edit from corrupting a canvas the user might simultaneously be dragging in. Atlas's canvas isn't editable that way (Non-Goal above), so there is no second live-writer to protect against, and `flow-management`'s spec already requires ungated live updates. Adding `Apply` here would be strictly a regression against a written scenario for no corresponding benefit. Rejected: porting `Apply` verbatim "for parity" — parity with the reference isn't the goal, parity with what the reference is *for* is.

**3. Monaco theme is Atlas-specific, not Gravity's playground theme.**
`Editor/theme.ts` themes to Gravity's own violet/orange brand (`#251b25` background, `#febe5c` keys) — that's their brand, not Atlas's. Monaco can't read `--g-color-*` custom properties directly, so this change defines two literal-color themes (`monacoFlowTheme.ts`), one per `.g-root_theme_light` / `.g-root_theme_dark`, using Atlas's actual resolved Gravity UI token values (see `frontend/src/theme.css` for Atlas's brand overrides) so the editor visually matches the rest of the app rather than importing a foreign brand. Rejected: shipping Monaco's default `vs`/`vs-dark` themes unstyled — would look visibly out of place next to Gravity UI's chrome.

**4. Client-side JSON Schema validates shape only; server remains authoritative.**
The schema (`flowStepSchema.ts`) describes `FlowStep[]` structurally (`id: string` required, `title`/`summary`/`entity_ref` optional strings, `next_step`/`next_steps` shape) so Monaco can catch typos and malformed JSON inline, before save. It cannot express — and does not attempt to express — `entity_ref` resolvability or the strict-tree/no-reconvergence rule; those stay exactly as today, validated server-side and surfaced through the existing API-error `Alert` in `FlowFormPage` on save. This mirrors the same layering `add-flows/design.md` already uses elsewhere (client does what it cheaply can, server is the source of truth).

**5. Zoom toolbar lives in `FlowGraph.tsx`, not `FlowFormPage.tsx`.**
`FlowGraph` is already shared between the edit page's preview pane and `FlowDetailPage`'s read-only view. Placing the toolbar inside the shared component means the read-only detail page gains working zoom/fit controls with zero changes to `FlowDetailPage.tsx` — the `zoomTo` call it needs is already destructured from `useGraph` (`FlowGraph.tsx:37`), just never exposed as UI. Ported closely from `Toolbox.tsx`: `Button view="raised"` + `@gravity-ui/icons` (`MagnifierPlus`/`MagnifierMinus`/`SquareDashed`), same floating vertically-centered pill CSS recipe (`Playground.scss`'s `__graph-tools`/`__zoom` pattern), adapted onto `.flow-graph` in `index.css` (which needs `position: relative` added — it currently has none).

**6. Node-click-to-JSON via a new optional `onBlockClick` prop, not a graph-wide event bus.**
`FlowGraph` gains `onBlockClick?: (stepId: string) => void`, wired only from `FlowFormPage` (which calls into a Monaco `scrollTo`-equivalent, ported from `findBlockPositionsMonaco`'s text-scan-for-`"id"` approach). `FlowDetailPage` simply doesn't pass the prop — clicking a node there does nothing new, which is correct since there's no editor pane to scroll to. This keeps the coupling one-directional and explicit rather than having `FlowGraph` reach for an editor ref it may not have.

**7. "Add Step" appends unwired JSON, no canvas placement.**
The original's "Add Block" places a new block at a computed/random canvas position because block position is freeform data in that model. Atlas's step position is never freeform (Non-Goal above) — so "Add Step" only needs to append `{ "id": "step-N", "title": "New step" }` (id generated to not collide with existing step ids) to the JSON array and scroll the editor to it via the same mechanism as Decision 6. The new step renders on the canvas already, disconnected, exactly like a freshly-dropped Gravity block before it's wired — the user connects it by hand-editing `next_step`/`next_steps`, consistent with `add-flows/design.md` Non-Goal "No structured/form-driven step builder."

## Risks / Trade-offs

- **[Monaco bundle weight]** Multi-MB dependency for what is currently a lean Vite app → **Mitigation**: `@monaco-editor/react`'s default CDN loader lazy-loads Monaco itself; only visited on `/flows/new` and `/flows/:id/edit`, not the app shell or the more heavily-trafficked read-only pages.
- **[Client/server validation drift]** The client-side JSON Schema (Decision 4) could fall out of sync with server-side validation rules in `apps/catalog/models/flow.py` if either changes independently → **Mitigation**: the schema only covers shape (already implicitly duplicated by the TypeScript `FlowStep` type today); the rules that can actually drift (entity-ref resolution, strict-tree) are deliberately *not* duplicated client-side, so there's nothing semantic to go stale.
- **[Two hand-maintained Monaco themes]** Light/dark theme colors are literal, not token references, so an Atlas palette change (`theme.css`) won't automatically propagate to the editor → **Mitigation**: scoped to two small files (`monacoFlowTheme.ts`), same category of manual upkeep the original already accepts for its own theme.

## Migration Plan

1. Add `@monaco-editor/react` to `frontend/package.json`.
2. Add `frontend/src/lib/flowStepSchema.ts` (JSON Schema for `FlowStep[]`) and `frontend/src/lib/monacoFlowTheme.ts` (light/dark theme defs + a small `findStepRange`-style utility for scroll-to-step).
3. Add the zoom toolbar + `onBlockClick` prop to `FlowGraph.tsx`; adjust `.flow-graph` CSS in `index.css` for `position: relative` and the floating toolbar.
4. Swap `FlowFormPage.tsx`'s `<TextArea>` for the Monaco editor, wire `onBlockClick` to scroll-to-step, add the "Add Step" button and the JSON-panel collapse toggle.
5. Manually verify: typing invalid JSON surfaces inline errors without losing the last-valid preview; clicking a canvas node scrolls/selects its JSON; zoom/fit works on both the edit preview and the read-only detail page; dark-theme toggle (if present in the app) keeps the editor legible.

No backend changes, no data migration, no rollback concerns beyond a standard revert.

## Open Questions

- Should the collapsed-JSON-panel state persist (e.g. per-user, via localStorage) across visits, or always reset open? Defaulting to "always open" unless the user asks otherwise — cheap to add later if wanted.
