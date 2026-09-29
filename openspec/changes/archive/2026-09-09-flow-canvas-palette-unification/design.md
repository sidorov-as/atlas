## Context

The Flow canvas (`plugins/flows/frontend`) renders 10 node kinds (`FlowNodeKind` in `flowNodeKind.ts`): six entity-backed kinds derived from `entity_ref`'s prefix (actor/team/service/data/api/system), External (derived from `external_label`), Query/Event (derived from `query_ref`/`event_ref`), and Step (the fallback — no ref of any kind).

Three visual styles coexist today in `FlowNodes.tsx`:
- Entity-backed + External: `PaletteNodeCard` with a tinted pastel fill, colored border (1px, 2px for System), and colored title/subtitle text — colors sourced from `FLOW_NODE_PALETTE`, itself a documented, deliberate duplication of the `c4` plugin's `_ATLAS_PLANTUML_TAGS` hex values.
- Query/Event: same `PaletteNodeCard`, but white fill and a bold border — added later (`add-flow-query-event-steps`) specifically because a tinted fill made a GET Query card indistinguishable from an API card. `boldBorder` exists to compensate for the lost fill contrast.
- Step: its own component, neutral card, a small colored Gravity UI `Label` chip carrying one of six fixed semantic themes (`label_theme: normal/info/success/warning/danger/utility`), a hardcoded `Flag` icon, uncolored (neutral gray) border.

This inconsistency, plus Step's inability to carry a distinct color beyond six semantic names or any per-instance icon, motivated a design conversation (captured in full in this change's originating thread) that arrived at the decisions below. This design.md records those decisions; it does not re-open them.

`_ATLAS_PLANTUML_TAGS` colors were tuned as fill/text pairs for pastel backgrounds — a different visual job than what's needed once fill goes neutral (a border color and a small chip background need to read clearly against a neutral card in both light and dark themes). Atlas already runs real theme switching (`ThemeProvider theme="system"` in `core/frontend/src/App.tsx`), so this is a live constraint, not a hypothetical one.

## Goals / Non-Goals

**Goals:**
- One consistent card anatomy for all 10 node kinds: neutral theme-aware fill, plain (uncolored) title/subtitle text, a small colored icon+label chip, and a bold (2px) colored border as the primary kind-identity signal.
- Step becomes a single, fully generic, customizable kind (title, summary, color, optional icon) that can stand in for any ad-hoc step concept.
- A theme-aware (light/dark-coordinated) node color palette, independent of the `c4` plugin's PlantUML palette.
- Reuse `@gravity-ui/icons` (already a dependency, already backs every kind's fixed icon) for Step's icon picker — no new package.

**Non-Goals:**
- No dedicated Retry/Schedule/Notification/Manual-approval/Decision/Projection/etc. node kinds. Explicitly rejected in favor of one generic Step — the taxonomy EventCatalog's editor uses was the original inspiration for this exploration but is deliberately not being adopted.
- No separate "Custom" kind alongside Step. One generic kind, not two overlapping ones.
- No "Type label" free-text override or per-node "URL" field (both present on EventCatalog's Custom node) — not requested, not in scope.
- No change to node kind *derivation* logic (`flowNodeKindOf`) — entity-backed/External/Query/Event kinds are still derived the same way; only their rendering and color source change.
- No change to keep Flow's canvas and the `c4` plugin's PlantUML diagram visually matched — they're allowed to diverge now that the palette duplication is intentionally ended.
- No backend/API changes — this stays within the existing Flow `steps` JSON grammar and its frontend schema/validation.

## Decisions

### 1. Step absorbs "Custom" — one generic kind, not two

Step gains: an optional per-instance `icon` (from `@gravity-ui/icons`) and a per-instance `color` (see Decision 3) alongside its existing `title`/`summary`. No new kind is added. The node-type picker (`FlowStepModal.tsx`'s `KIND_TILES`) keeps its single "Step" tile; its config panel gains an icon-picker control next to the (redefined) color control.

Alternative considered: a distinct "Custom" tile alongside a bare, uncolored "Step" tile (EventCatalog's own model, where Step and Custom are separate). Rejected — Step already carries everything Custom would add on top of; splitting them would mean two overlapping config panels and two tiles a user has to choose between for what's conceptually one kind of node.

Alternative considered: dedicated kinds for common concepts (Retry, Schedule, Notification, Manual approval). Rejected — the cost (new schema fields, new `flowNodeKindOf` branches, new palette entries, new fixed icons per kind, unbounded — every org has different vocabulary) outweighs the benefit (enforced visual consistency for a fixed vocabulary Atlas doesn't own) for a canvas that already deliberately scoped down from EventCatalog's ~17 kinds to 8 in the original `flow-canvas-redesign` change. A generic, icon+color+title Step can represent any of these today, at the cost of consistency being the author's responsibility rather than the schema's — accepted as a reasonable trade for keeping the schema and derivation logic simple.

### 2. Card anatomy unifies to Step's current shape

Every kind's card converges on the shape Step already has, rather than something new being invented:

```
┌──────────────────┐
│ [🧑 ACTOR]         │  ← small colored chip: icon + kind label (fill/text from the
│                    │     kind's color; unchanged in spirit from today's Step Label
│  Checkout Widget   │     chip, now used by every kind)
│  user:checkout-... │  ← plain text (no color from `colors.text`)
└────────────────────┘
   border: 2px, colored (Decision 3)
   fill:   neutral, theme-aware (Decision 4)
```

Concretely in `FlowNodes.tsx`: `PaletteNodeCard`'s icon+bold-text type row is replaced with a small chip component (visually equivalent to `StepNodeComponent`'s current `Label` usage) shared by every kind; its title/subtitle `Text` no longer takes `color={colors.text}`; its `background`/`border` styling is unified with `StepNodeComponent`'s. `StepNodeComponent` and `PaletteNodeCard` likely collapse into one component once their only remaining difference is where the color comes from (fixed per kind vs. per-instance for Query/Event/Step) — an implementation detail for tasks.md, not a design commitment here.

### 3. Border is the primary kind-identity signal: bold + colored, universally

Every card's border is 2px and colored — not just System's, which was already 2px. Rationale: once fill no longer carries color, the border (and the small chip) are the only two channels left to distinguish kinds at a glance; keeping most borders thin would under-differentiate the canvas.

- Entity-backed (actor/team/service/data/api/system) and External: fixed color per kind, from the new palette (Decision 4).
- Query/Event: unchanged inputs (snapshotted HTTP method / direction), now also driving a 2px border instead of the old fill/boldBorder combination.
- Step: the author's chosen per-instance color (Decision 1) now drives its border too, not just its chip — Step's border stops being neutral gray. Without this, Step would be the one card that doesn't participate in the system every other kind now follows, i.e. visually weaker than everything else on the same canvas.

The `boldBorder` prop/mechanism in `PaletteNodeCard` (added to compensate for white fill on Query/Event) is removed as a concept — bold is now universal, so there's nothing left to conditionally compensate for. System's 2px weight is kept, but its justification changes: it's no longer "the one bold exception," it's "every border is this weight now," and System's specific hex is still sourced from `_ATLAS_PLANTUML_TAGS`'s bold C4 tag (Decision 4 explains why that sourcing itself is being retired for color, not weight).

### 4. Palette: decoupled from C4, theme-aware

`flowNodePalette.ts` is rewritten from fixed hex triples (`{fill, text, border}`) copied from `_ATLAS_PLANTUML_TAGS` to a theme-aware token set — CSS custom properties with coordinated light/dark values, one border/chip color per kind (fixed for the 7 entity/external kinds; the palette also defines the Query method-color and Event direction-color tables, unchanged in structure, just re-expressed as theme-aware tokens instead of fixed hex).

This intentionally ends the "deliberate, documented duplication" of `c4`'s PlantUML palette that `flowNodePalette.ts` currently calls out in its own comments. Flow's canvas (React Flow, live theme switching) and `c4`'s diagrams (server-rendered PlantUML SVG, no theme awareness today) are different rendering pipelines; requiring them to share one fixed hex table was already an awkward coupling across a plugin boundary, and it blocks dark-mode support for Flow specifically. They're expected to look different after this change — not a regression, a deliberate decoupling now that there's a concrete reason (theme support) to want one.

Alternative considered: keep fixed hex (simpler, one table, matches how Query/Event's method colors work today). Rejected per explicit product direction — dark mode / additional themes are a near-term goal, and repainting this system twice (once now, once again for dark mode) is worse than doing the coordinated light/dark token work now while every node's rendering is already being touched.

Step's color picker in `FlowStepModal.tsx` exposes this same palette's kind-independent swatches (i.e., the same visual color set used for fixed-kind borders elsewhere, offered as user-selectable choices for Step) rather than a separate, unrelated swatch set — one palette, two consumption modes (fixed-by-kind, chosen-by-author).

### 5. Step schema: `label_theme` → `color` + `icon`

`flowStepSchema.ts`'s `label_theme: 'success' | 'danger' | 'warning' | 'info' | 'utility' | 'normal'` is replaced by two new optional fields on a step: `color` (a key into the new palette's swatch set) and `icon` (a `@gravity-ui/icons` component name, validated against that package's `metadata.json`-derived name list). This is a breaking shape change for any flow with a stored `label_theme` (see Migration Plan).

## Risks / Trade-offs

- **[Breaking schema change]** Existing flows with `label_theme` on a Step lose their stored color shape. → Migration Plan below: a one-time value mapping (six semantic names → six swatches in the new palette) applied on load/save, plus a rendering fallback so an unmigrated flow doesn't render an uncolored/broken Step in the interim.
- **[Consistency is no longer enforced]** Because Step is fully generic (Decision 1), two authors modeling "a retry step" may pick different icons/colors/titles, unlike a dedicated Retry kind which would look identical everywhere. → Accepted trade (see Decision 1's alternative-considered writeup); revisit only if this becomes an observed pain point, e.g. by adding a lightweight preset-shortcut inside Step's config panel later (not in this change).
- **[Palette redesign is subjective/visual]** Choosing 2px-bold, theme-aware colors that read clearly for 7+ fixed kinds plus Query's 7 method colors plus Event's 2 direction colors, in both light and dark, is a real visual-design task, not a mechanical port of existing hex values. → Scope this as its own task in tasks.md with explicit light+dark review, not a drive-by rename of existing constants.
- **[Flow/C4 visual divergence]** Users who cross-reference a Flow diagram against a C4 diagram for the same system lose the today-shared color mapping. → Accepted per explicit product direction; no mitigation planned.

## Migration Plan

1. Add `color`/`icon` (optional) to `flowStepSchema.ts` alongside the still-present (but deprecated) `label_theme`, so existing flow JSON keeps validating during the transition.
2. Ship a `label_theme` → `color` mapping table (six semantic names → six specific swatches in the new palette) and apply it wherever a step is read for rendering, so unmigrated flows render correctly with no author action required.
3. `FlowStepModal.tsx`'s Step edit path writes `color`/`icon` going forward; saving any step (even without touching its color) rewrites `label_theme` away in favor of `color`, so the field naturally drains out of active flows over time.
4. Once `label_theme` usage in stored flows is negligible (operationally, not schema-enforced), drop it from `flowStepSchema.ts` in a follow-up change — not part of this one, to avoid coupling a rendering/palette change to a hard data migration deadline.

## Open Questions

- Exact swatch set (names/count) and their light/dark hex values for the new theme-aware palette — a visual-design task to do alongside implementation, not resolved here.
- Default rendering for a Step with no chosen color (a true neutral/no-color state, distinct from "user picked a swatch") — needs a defined default swatch or an explicit neutral fallback so an unstyled Step doesn't look broken.
