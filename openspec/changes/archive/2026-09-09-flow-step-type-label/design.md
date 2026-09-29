## Context

Step (`plugins/flows/frontend`) is Flow's generic, non-entity-backed node kind: title, summary, an author-chosen color, and an author-chosen icon (`flow-canvas-palette-unification`). Every node kind renders one shared card anatomy (`FlowNodes.tsx`'s `NodeCard`) with a small colored chip carrying an icon + label. For every fixed/derived kind, that chip's label is either a constant (`FLOW_NODE_KIND_LABELS`, e.g. "Service") or derived from the step's own ref (Query/Event). Step's chip label is currently the same fixed constant, "Step" — the one thing about Step's rendering that isn't author-customizable despite Step itself being the fully-generic kind.

`flow-canvas-palette-unification`'s design.md explicitly deferred this ("No 'Type label' free-text override ... not requested, not in scope") when scoping down from EventCatalog's model. It's now requested, scoped narrowly to just Step's chip text — this design does not reopen any other decision from that change (palette, card anatomy, icon picker, etc. all stand as shipped).

## Goals / Non-Goals

**Goals:**
- Step's chip can show an author-chosen short label (e.g. "Retry", "Manual Approval") instead of always "Step".
- Zero migration: a Step with no `type_label` renders exactly as it does today ("Step"), including every already-authored flow.

**Non-Goals:**
- No change to any other kind's label (fixed or derived) — this is Step-only, matching Step's unique role as the one generic kind.
- No length limit, format validation, or icon-per-label mapping — free text, same laxness as `title`/`summary`.
- No equivalent of EventCatalog Custom node's per-node "URL" field — still not requested.

## Decisions

### 1. `type_label`: a new optional field, not a repurposing of an existing one

Step gains `type_label?: string` (free text) alongside its existing `color`/`icon`/`title`/`summary`. Rejected alternative: overload `title` or add a convention like a leading `[Label]` prefix — both would conflate the node's identity (title) with its category (chip), which is exactly the distinction the rest of the canvas already draws (every other kind keeps title and chip-label separate).

### 2. Resolution: chosen value wins, fixed constant is the fallback

A new resolver in `flowNodeKind.ts`, `stepTypeLabel(step)`, returns `step.type_label` when it's a non-blank string, else `FLOW_NODE_KIND_LABELS.step` ("Step") — the same shape as `stepIcon`'s existing `step.icon ?? default` pattern, so `StepNodeComponent` (`FlowNodes.tsx`) swaps one constant lookup for one resolver call with no other change to `NodeCard`'s anatomy. Blank/whitespace-only input is treated as unset (trimmed check) so clearing the field in the UI visibly reverts to "Step" rather than rendering an empty chip.

### 3. Modal: a plain text input, not a preset list

`FlowStepModal.tsx` gets one new optional `TextInput` for "Type label" in Step's field group (alongside color swatches and the icon picker), placeholder "Step" (mirrors the resolver's own fallback so the placeholder never lies about what an empty field will render as). Rejected alternative: a `Select` of common presets (Retry/Notification/Manual Approval/...) — rejected for the same reason `flow-canvas-palette-unification` rejected dedicated node kinds for these concepts: the vocabulary isn't Atlas's to own, and a free-text field already covers every preset as a special case with none of the maintenance cost.

## Risks / Trade-offs

- **[Free text, no enforced vocabulary]** Two authors describing "a retry step" may type different labels ("Retry" vs "Retry attempt"). → Accepted; same trade-off already made for Step's color/icon by the parent change, and for `title`/`summary` from the start.
- **[Blank vs whitespace]** A `type_label` of `"   "` must still fall back to "Step", not render a blank chip. → Resolver trims before the non-blank check (Decision 2); tested explicitly (tasks.md).

## Migration Plan

None needed — `type_label` is a new optional field; every existing step (unset) resolves to today's "Step" via the fallback with no read-time transform and no write-time rewrite.
