## 1. Backend: dialect registry & model

- [x] 1.1 Add `mysql` and `mssql` to `DatabaseSchema.DIALECT_CHOICES` plus an additive migration
- [x] 1.2 Add the `sqlglot` dependency to `plugins/database-schema/backend/pyproject.toml`
- [x] 1.3 Define the dialect→sqlglot registry (`postgresql→postgres`, `mysql→mysql`, `mssql→tsql`) as a single lookup, not per-dialect branches
- [x] 1.4 Widen `api/schemas.py`'s `DatabaseSchemaDialect` Literal from `postgresql`-only to all three choices (gap in proposal.md's Impact section, which claimed no contract change was needed)

## 2. Backend: sqlglot-based parser

- [x] 2.1 Replace `parser.py`'s regex implementation with a sqlglot-based parser producing the tbls-compatible shape: `tables[].{name, type, columns[], indexes[], constraints[]}`, top-level `relations[]`, and `enums[]`
- [x] 2.2 Map sqlglot parse failures onto the existing `SqlParseError` / `parse_status=failed` contract so `_apply_source` needs no behavior change
- [x] 2.3 Rewrite `tests/test_parser.py` to cover all three dialects, including enum types, generated columns, partial indexes, and `ALTER TABLE ADD CONSTRAINT ... FOREIGN KEY`
- [x] 2.4 Update `tests/test_views.py` / `conftest.py` fixtures that assume the old `parsed_schema` shape or the single-dialect default

## 3. Frontend: dialect selection

- [x] 3.1 Add a dialect `<Select>` (PostgreSQL/MySQL/MS SQL) to `SchemaEditorTab.tsx`, replacing the hardcoded "PostgreSQL schema" label
- [x] 3.2 Thread the selected dialect through `databaseSchemaApi.create`/`update` (currently only sends `source_sql`)
- [x] 3.3 Update `SchemaEditorTab.test.tsx` for the new field

## 4. Frontend: React Flow ER viewer

- [x] 4.1 Resolve design.md's open question on elkjs vs. dagre, then add React Flow (`@xyflow/react`), the chosen autolayout library, and an export/rasterization library to `plugins/database-schema/frontend/package.json`
- [x] 4.2 Build a table node component (name header, columns with type/PK/FK markers)
- [x] 4.3 Map `parsed_schema.relations[]` to React Flow edges between column handles
- [x] 4.4 Enforce read-only interaction: `nodesConnectable={false}`, no add/remove-node UI; keep `nodesDraggable` for repositioning only
- [x] 4.5 Implement an autolayout button that repositions nodes on press without overwriting manual drags in between presses
- [x] 4.6 Build the zoom-in/zoom-out/fit-to-viewport button cluster matching the C4 viewer's icon set (`MagnifierPlus`/`MagnifierMinus`/`SquareDashed`) and placement, wired to `useReactFlow()`
- [x] 4.7 Add SVG and PNG export buttons using the chosen client-side rasterization library
- [x] 4.8 Enable `onlyRenderVisibleElements` conditionally above a defined table-count threshold
- [x] 4.9 Replace `ErDiagramView.tsx`'s card layout with the new graph view
- [x] 4.10 Resolve design.md's open question on old-shape `parsed_schema` detection, then implement the fallback in the view layer

## 5. Frontend: failure banner

- [x] 5.1 Replace `ErDiagramTab.tsx`'s plain-text parse-failure message with an `Alert theme="danger"` banner, matching the tab's existing load-failure `Alert`
- [x] 5.2 Update `ErDiagramTab.test.tsx` / `ErDiagramView.test.tsx` for the new failure UI and the new view component

## 6. Validation

- [x] 6.1 Manually verify all three dialects end-to-end: paste DDL, save, confirm the graph renders with correct tables and relations
- [x] 6.2 Manually verify a deliberately malformed schema shows the ER Diagram tab's error banner while the Schema tab still preserves the saved SQL
- [x] 6.3 Manually verify SVG and PNG export downloads and visually matches the on-screen diagram
- [x] 6.4 Confirm a distribution without `atlas.database-schema` still composes and shows no Schema/ER Diagram tabs (existing optional-plugin requirement, unchanged)
