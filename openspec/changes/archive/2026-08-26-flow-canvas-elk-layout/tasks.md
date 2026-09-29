## 1. ELK dependency spike

- [x] 1.1 Add `elkjs` to `frontend/package.json`
- [x] 1.2 Spike importing `elkjs` in the Vite dev/build setup; confirm whether the worker-based default export works as-is or the bundled non-worker variant (`elkjs/lib/elk.bundled.js` or equivalent) is needed
- [x] 1.3 Record the chosen import shape as a short note in `design.md`'s Open Questions (resolve, don't leave dangling)

## 2. ELK-driven layout

- [x] 2.1 In `frontend/src/lib/flowLayout.ts`, replace `sizeSubtree()`/`assignPositions()` with block positions sourced from `@gravity-ui/graph`'s `useElk` hook (`elk.direction: RIGHT`), keeping `buildForest()`, `flatten()`, and connection/label construction as-is
- [x] 2.2 Confirm the forest's mid-edit tolerance (`buildForest()`'s handling of cycles/reconvergence during live JSON editing) still produces a renderable ELK graph — feed each forest root as its own ELK layout call, or a single multi-root graph, whichever keeps this behavior intact
- [x] 2.3 Update `FlowBlock`/`FlowLayout` types if the hook's async result shape requires it

## 3. Async live-preview handling

- [x] 3.1 In `FlowGraph.tsx`, debounce the `steps` input feeding the layout computation (a few hundred ms of no change)
- [x] 3.2 While a new layout is pending, keep rendering the previously-computed blocks/connections — never call `setEntities` with a partial or empty result
- [x] 3.3 Manually verify against the "Live preview updates as the JSON is edited" spec scenario: typing in the Monaco editor still updates the diagram without requiring a save, and without a visible blank/flicker state

## 4. Connection labels

- [x] 4.1 Add `showConnectionLabels: true` to `GRAPH_CONFIG.settings` in `FlowGraph.tsx`
- [x] 4.2 Verify a step's `next_step.label` / a `next_steps[]` entry's `label` renders on its connection, and that labels hide at low zoom (existing library behavior)
- [x] 4.3 Verify a transition with no `label` renders its connection unlabeled (no empty label box)

## 5. Visual palette

- [x] 5.1 Add a fixed `viewConfiguration.colors` block to `GRAPH_CONFIG` in `FlowGraph.tsx` (block background/border/selected-border, connection background/selected-background, anchor background, canvas dots/background/border), following the reference playground's recipe (`temp/landing/src/components/GraphPlayground/Playground/GraphPlayground.tsx`)
- [x] 5.2 Restyle `.flow-graph__block` (and related rules) in `frontend/src/index.css` to match, replacing the current generic `--g-color-*` token usage
- [x] 5.3 Manually verify the diagram on both the read-only Flow detail page and the edit page's live preview picks up the new palette

## 6. Spec and regression pass

- [x] 6.1 Re-verify all existing `flow-management` diagram scenarios still hold: zoom/fit controls, click-node-to-JSON scroll, "Add Step" appending an unconnected node, malformed-JSON inline error without discarding the last preview
- [x] 6.2 Confirm no backend, API, or `steps` JSON shape changes were introduced
