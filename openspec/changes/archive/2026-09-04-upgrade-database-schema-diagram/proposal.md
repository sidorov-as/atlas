## Why

The `database-schema-plugin`'s ER Diagram view was built as a proof point for the Facet/view split, not as a finished feature: its parser is a hand-rolled regex tokenizer explicitly bounded to PostgreSQL `CREATE TABLE` statements, and its view is a plain flex-wrap card layout with no graph, no edges, no zoom, and no export — both self-documented in code as provisional ("no external contract promised", "not a graph-layout engine"). The Facet already carries a `dialect` field, but there is no UI to set it and only one dialect is implemented. Meanwhile the catalog already has a UX bar for diagram viewers (the C4 plugin's zoom/fit/export chrome) that this feature doesn't meet. This change upgrades the parser to sqlglot (real multi-dialect AST instead of regex) and the view to a read-only, ChartDB-style React Flow graph, without changing the plugin's Facet/API contract.

## What Changes

- Replace the regex-based `parser.py` (PostgreSQL-only, `CREATE TABLE`-only) with a sqlglot-based parser that produces a tbls-compatible `parsed_schema` shape: `tables[].{name, type, columns[], indexes[], constraints[]}`, a top-level `relations[]` (table/columns/parent_table/parent_columns/cardinality), and `enums[]`. Indexes and constraints are captured and stored even though the viewer will not render them yet.
- Expand `DatabaseSchema.dialect` from PostgreSQL-only to PostgreSQL / MySQL / MS SQL, and add a dialect `<Select>` to the Schema tab (`SchemaEditorTab.tsx`), replacing the hardcoded "PostgreSQL schema" label. **BREAKING**: the Schema tab's fixed PostgreSQL-only framing goes away — existing facets default to `postgresql` (unchanged behavior for current users).
- Map catalog dialect choices to sqlglot's dialect identifiers through a small registry (`postgresql → postgres`, `mysql → mysql`, `mssql → tsql`), not per-dialect branching in the parser, so adding a future dialect (e.g. Oracle, already supported by sqlglot) is a registry entry plus a migration, not a parser change.
- Replace `ErDiagramView.tsx`'s static card layout with a read-only React Flow canvas: table nodes with columns/PK/FK, real edges for relations, drag-to-reposition, and a button-triggered autolayout (no live editing — no adding/removing tables or connections). **BREAKING**: removes the current card-based rendering.
- Add a zoom-in / zoom-out / fit-to-viewport button cluster matching the C4 diagram viewer's visual style (`MagnifierPlus`/`MagnifierMinus`/`SquareDashed` icons, top-right `Tooltip` + `Button view="raised"` cluster) — reimplemented against React Flow's own `useReactFlow()` zoom/fit methods, not the C4 plugin's `<img>`-based `DiagramViewer` (which cannot support draggable nodes).
- Add SVG and PNG export of the rendered diagram.
- Replace the ER Diagram tab's plain-text parse-failure message with a visible error banner (`Alert theme="danger"`), consistent with the tab's existing load-failure `Alert`, so an invalid schema is saved but clearly flagged in the ER Diagram tab itself (not only on the Schema tab's `ParseStatusIndicator`).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `database-schema-plugin`: dialect is now a user-selectable field (PostgreSQL/MySQL/MS SQL) rather than a fixed, invisible default; the ER Diagram view requirement gains graph-rendering, zoom/pan/fit, and SVG/PNG export behavior; the failed-parse requirement gains an explicit ER-Diagram-tab-visible error scenario.

## Impact

- **Backend** (`plugins/database-schema/backend/atlas_plugin_database_schema/`): `parser.py` replaced by a sqlglot-based parser/mapper; `models/database_schema.py` gains two `DIALECT_CHOICES` entries plus a migration; `pyproject.toml` gains a `sqlglot` dependency; `tests/test_parser.py` rewritten for sqlglot across three dialects. `api/views.py` already threads `dialect` end-to-end and needs no change; `api/schemas.py`'s `DatabaseSchemaDialect` Literal widens from `postgresql`-only to all three choices — no shape change, but the allowed values do change.
- **Frontend** (`plugins/database-schema/frontend/`): `SchemaEditorTab.tsx` gains a dialect `<Select>`; `ErDiagramView.tsx` rewritten on a React Flow canvas; `ErDiagramTab.tsx` gains an `Alert`-based failure state; `package.json` gains a React Flow dependency, `elkjs` for autolayout, and `html-to-image` for export/rasterization.
- **No change** to the Facet's REST contract shape (`DatabaseSchemaIn`/`Out`/`Patch`), to the `entity-facets` ownership model, or to the `schema.host.v1` capability gating — this change is internal to the `database-schema` plugin.
