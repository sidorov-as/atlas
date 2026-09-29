## Why

The Flow canvas currently renders node kinds in three inconsistent visual styles: six entity-backed kinds (Actor/Team/Service/Data/API/System) plus External use tinted pastel card fills copied verbatim from the `c4` plugin's PlantUML palette; Query/Event use a white fill with a bold border (added later specifically because a tinted fill made a GET Query indistinguishable from an API card); and Step uses a neutral card with a small colored `Label` chip. The canvas reads as three different design systems stitched together rather than one. Separately, Step is the only kind an author can't visually customize beyond a fixed six-color semantic theme and a hardcoded icon, which is thinner than what's needed for a plain step to stand in for a wide range of ad-hoc concepts (a retry point, a manual approval, a notification) without Atlas having to grow a dedicated node kind for each one.

## What Changes

- Step becomes the single generic, fully-customizable non-entity-backed node kind. **No** dedicated Retry/Schedule/Notification/Manual-approval/etc. kinds are added, and there is no separate "Custom" kind alongside Step.
- Step gains an optional per-instance icon, chosen from `@gravity-ui/icons` via a searchable picker (built from that package's existing `metadata.json`; no new dependency).
- Step's existing `label_theme` (a fixed set of six semantic theme names) is replaced by a per-instance color chosen from the flattened palette (see below) — the same color now also drives Step's border, not just its type chip. **BREAKING**: `label_theme` is removed from the step schema; existing values are migrated to the closest equivalent color on save (old flows continue to render via a fallback until then).
- Every node kind's card fill flattens to one neutral, theme-aware background. The tinted `FLOW_NODE_PALETTE` fills for Actor/Team/Service/Data/API/System/External are removed.
- Title and subtitle text on every card renders in plain, neutral text — no kind ever colors its own title text (matching Step's current, unchanged behavior).
- Every card's border becomes the primary carrier of kind identity: bold (2px) and colored on every kind, not just System. Entity-backed kinds and External keep a fixed color per kind; Query/Event keep their existing per-instance color (HTTP method / direction); Step's border color is now the author's chosen per-instance color. The `boldBorder`-as-white-fill-compensation mechanic is removed as a concept — bold+colored is now universal, and System's 2px weight is kept because it's inherited from the C4 PlantUML tag definition, not because it was compensating for anything.
- The node color palette is decoupled entirely from `plugins/c4/backend/atlas_plugin_c4/c4.py`'s `_ATLAS_PLANTUML_TAGS` (today's `flowNodePalette.ts` explicitly documents that duplication; this change ends it). The new palette is defined as theme-aware values (coordinated light/dark, via CSS custom properties) rather than fixed hex, so the canvas can support dark mode / future themes without another rewrite. Flow's canvas and the C4 plugin's PlantUML diagrams are expected to diverge visually after this change — they render on different pipelines and are no longer required to match.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `visual-flow-editor`: the node-type picker's Step fields change (icon added, color model changes from a fixed semantic theme to the flattened per-instance palette); every node kind's visual rendering (fill, border, text, type badge) changes to the unified neutral-card/colored-border/chip style described above.

## Impact

- `plugins/flows/frontend/src/lib/flowNodePalette.ts` — palette redefined (theme-aware, decoupled from C4); `label_theme`'s six-name enum retired from the color story.
- `plugins/flows/frontend/src/lib/flowStepSchema.ts` — Step step shape: `label_theme` removed, `color` and `icon` (both optional) added.
- `plugins/flows/frontend/src/lib/flowNodeKind.ts` — icon map changes from one fixed icon per kind to a per-kind default plus a per-instance override for Step.
- `plugins/flows/frontend/src/components/FlowNodes.tsx` — `PaletteNodeCard`/`StepNodeComponent` rendering rewritten to the unified card anatomy; `boldBorder`/fill-compensation logic removed.
- `plugins/flows/frontend/src/components/FlowStepModal.tsx` — Step's color `Select` replaced by the flattened palette's swatches; new icon-picker control added; `TILE_COLORS`/`NEUTRAL_TILE_COLORS` updated for the new palette shape.
- Existing flows with a stored `label_theme` need a migration path (data shape change, not just a rendering change) — addressed in design.md.
- `openspec/specs/visual-flow-editor/spec.md` — requirement text and scenarios touching Step's fields and node visual styling.
- No backend/API changes — this is a frontend rendering and step-schema change within the existing Flow steps JSON grammar.
