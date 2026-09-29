## 1. Palette redesign

- [x] 1.1 Design the theme-aware (light/dark-coordinated) color set in `flowNodePalette.ts`: one identity color per entity-backed kind (Actor/Team/Service/Data/API/System) and External, expressed as CSS custom properties rather than fixed hex.
- [x] 1.2 Re-express Query's HTTP-method color table and Event's direction color table as theme-aware tokens, preserving their existing method/direction → color mapping structure.
- [x] 1.3 Define the swatch set Step's color picker offers, drawn from the same palette (not a separate ad-hoc set), including a default swatch for a Step with no explicitly chosen color.
- [x] 1.4 Remove the `_ATLAS_PLANTUML_TAGS`-sourced fixed hex values and the file-header comment documenting that duplication; replace with a comment noting the palette is now independent of the `c4` plugin.
- [x] 1.5 Visually review the full palette in both light and dark theme (`ThemeProvider theme="system"`), checking border and chip legibility against the shared neutral card background for every kind.

## 2. Step schema and data migration

- [x] 2.1 Add optional `color` and `icon` fields to `flowStepSchema.ts`'s step shape; keep `label_theme` accepted (deprecated) for backward compatibility during migration.
- [x] 2.2 Add the `label_theme` → `color` mapping table (six semantic names → six palette swatches).
- [x] 2.3 Apply the mapping at render time so a step with only `label_theme` set (no `color`) still renders with a correct color, without requiring the flow to be re-saved.
- [x] 2.4 Update `FlowStepModal.tsx`'s save path so saving any Step writes `color` (and clears `label_theme`) going forward, per the Migration Plan in design.md.
- [x] 2.5 Validate `icon` values against `@gravity-ui/icons`' known component/icon names (from its `metadata.json`), rejecting unknown values the same way other schema fields are validated.

## 3. Node kind and icon plumbing

- [x] 3.1 Update `flowNodeKind.ts`'s icon map: keep one default icon per fixed kind, and support a per-instance icon override for Step (falling back to Step's default icon when none is chosen).
- [x] 3.2 Build an icon-name → icon-component lookup backed by `@gravity-ui/icons`, keyed the same way its `metadata.json` names icons, for use by both the icon picker (task 5) and node rendering.

## 4. Unified card rendering

- [x] 4.1 Rewrite `PaletteNodeCard` in `FlowNodes.tsx` to the unified anatomy: neutral theme-aware fill, plain (uncolored) title/subtitle text, a small colored icon+label chip, and a bold (2px) colored border — replacing the current tinted-fill/colored-text styling for entity-backed and External kinds.
- [x] 4.2 Remove the `boldBorder` prop/mechanism (the white-fill compensation it existed for no longer applies); keep System's 2px border, sourced from the new palette rather than `_ATLAS_PLANTUML_TAGS`.
- [x] 4.3 Update `QueryNodeComponent`/`EventNodeComponent` to the unified anatomy, keeping their per-instance (method/direction) color source.
- [x] 4.4 Update `StepNodeComponent` to render its chosen icon (task 3) and color consistently on both its border and its chip, matching the anatomy every other kind now uses; evaluate whether `StepNodeComponent` and `PaletteNodeCard` should collapse into one shared component now that their only remaining difference is where color/icon come from.
- [x] 4.5 Confirm `AddPlaceholderNode` and delete/add controls still render correctly against the new neutral card background.

## 5. Step config panel

- [x] 5.1 Replace the `label_theme` `Select` in `FlowStepModal.tsx`'s Step fields with a swatch picker over the new palette's Step color set (task 1.3).
- [x] 5.2 Add a searchable icon picker (name/keyword search over `@gravity-ui/icons`' `metadata.json`) as a new optional field in the Step config panel, with a way to clear back to "no icon" (default Step icon).
- [x] 5.3 Update `TILE_COLORS`/`NEUTRAL_TILE_COLORS` and the node-type picker's tile previews to reflect the flattened palette's colors instead of the retired `FLOW_NODE_PALETTE` tints.

## 6. Spec and documentation alignment

- [x] 6.1 Confirm `plugins/flows/frontend/src/lib/flowNodePalette.ts`'s file-header comments and any other in-repo references to `_ATLAS_PLANTUML_TAGS`/C4 palette duplication are updated or removed to match the new sourcing.
- [x] 6.2 Update or add component/unit tests covering: Step rendering with a chosen color+icon, Step rendering with only a legacy `label_theme` (migration fallback), and each fixed kind's border/chip color.
- [x] 6.3 Manually verify the canvas in the running app (light and dark) against `openspec/specs/visual-flow-editor/spec.md`'s new "Unified node visual styling" scenarios before marking this change ready to archive.
