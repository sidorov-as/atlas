## 1. Schema and types

- [x] 1.1 Add optional `type_label` (free-text string) to `flowStepSchema.ts`'s step shape.
- [x] 1.2 Add `type_label?: string` to `core/frontend/src/lib/types.ts`'s `FlowStep` interface.

## 2. Resolver and rendering

- [x] 2.1 Add a `stepTypeLabel(step)` resolver in `flowNodeKind.ts`: returns `step.type_label` when it's a non-blank (trimmed) string, else `FLOW_NODE_KIND_LABELS.step` ("Step") — mirrors `stepIcon`'s chosen-value-with-fallback shape.
- [x] 2.2 Update `StepNodeComponent` in `FlowNodes.tsx` to pass `stepTypeLabel(step)` as `NodeCard`'s `label` prop instead of the fixed `FLOW_NODE_KIND_LABELS.step` constant.

## 3. Step config panel

- [x] 3.1 Add an optional "Type label" `TextInput` to `FlowStepModal.tsx`'s Step field group, alongside the existing color swatches and icon picker; placeholder "Step".
- [x] 3.2 Wire the field's state through the modal's save path so saving a Step writes `type_label` (or omits it when blank/unset, consistent with how `summary` is handled).

## 4. Tests

- [x] 4.1 Unit test `stepTypeLabel`: chosen value wins, blank/whitespace-only falls back to "Step", unset falls back to "Step".
- [x] 4.2 Component test: `StepNodeComponent` chip renders a custom `type_label` when set, and renders "Step" when unset — extend `FlowNodes.test.tsx`'s existing Step describe block.
- [x] 4.3 `flowSteps.test.ts`: round-trip `type_label` through `parseFlowSteps`/`serializeFlowSteps` alongside the existing `color`/`icon` round-trip test.

## 5. Spec alignment

- [x] 5.1 Confirm `openspec/specs/visual-flow-editor/spec.md`'s merged text (after `flow-canvas-palette-unification` archives) matches this change's delta scenarios for Step's type label; reconcile via `/opsx:update` if archive order caused drift.
