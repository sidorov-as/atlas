## Why

The Database schema editor (`SchemaEditorTab`) and the API spec inline editor (`ApiFormPage`) both accept structured text — SQL `CREATE TABLE` statements and OpenAPI/AsyncAPI YAML-or-JSON documents — through a plain Gravity UI `TextArea` with no syntax highlighting, no bracket/quote matching, and no feedback on malformed content until after save. Flow's editor already solved this for JSON with Monaco (`plugins/flows/frontend`), but that setup is private to the Flow plugin — there's no reusable editor component plugins can adopt without duplicating Monaco wiring and theming from scratch.

## What Changes

- Add a new shared `CodeEditor` component in `core/frontend`, wrapping `@monaco-editor/react`, generalizing the theme approach currently private to `plugins/flows/frontend/src/lib/monacoFlowTheme.ts` (light/dark themes matching Atlas's Gravity UI palette) so it isn't Flow-specific.
- The shared component supports `language: 'sql' | 'yaml' | 'json'` (Monaco's built-in tokenizers; no custom dialect-specific SQL grammar).
- `SchemaEditorTab` (`plugins/database-schema/frontend`) switches its SQL input from `TextArea` to the shared `CodeEditor` with `language="sql"`. The existing `DIALECT_OPTIONS` select is unchanged and continues to affect save/parse behavior only, not highlighting — Monaco has one generic `sql` tokenizer, not per-dialect grammars.
- `ApiFormPage`'s inline spec field (`plugins/apis/frontend`) switches from `TextArea` to the shared `CodeEditor`. Since `spec_content` carries no stored format discriminator (verified: it's a plain `TextField`, parsed by both backend and frontend through one YAML-or-JSON-tolerant parser — `yaml.safe_load` / `js-yaml`), the editor detects JSON vs. YAML client-side by sniffing the trimmed content's leading character (`{` or `[` → `json`, otherwise → `yaml`) and switches Monaco's `language` prop accordingly.
- The API spec editor surfaces a visible inline error when its content fails to parse as valid JSON/YAML, before save — mirroring how `FlowFormPage` already surfaces Monaco validation state.
- **Out of scope**: migrating Flow's own JSON editor onto the new shared component. Flow's current private Monaco setup is left untouched by this change; adopting the shared component there is a candidate follow-up, not part of this proposal.
- **Out of scope**: SQL dialect-aware highlighting (e.g. distinguishing Postgres/MySQL/MSSQL keywords). Only generic SQL tokenization is added.
- **Out of scope**: autocomplete, schema-aware validation, or any change to what gets persisted — this is a client-side editing affordance only.

## Capabilities

### New Capabilities
- `code-editor`: a shared, theme-aware Monaco-based code editor component in `core/frontend`, supporting SQL/YAML/JSON syntax highlighting and exposing parse-validity feedback to its caller, for reuse by any plugin that needs to edit structured text.

### Modified Capabilities
- `database-schema-plugin`: the Database Schema facet editor's SQL input gains syntax highlighting via the shared `code-editor` component (`SchemaEditorTab`); no change to save, parse, or dialect-selection behavior.
- `api-spec-documents`: the inline spec source's editor gains syntax highlighting (auto-detected JSON/YAML) via the shared `code-editor` component, and surfaces a visible parse error for invalid JSON/YAML content before save.

## Impact

- **New dependency wiring**: `core/frontend` gains its first actual consumer of the already-declared `@monaco-editor/react` dependency (component code + theme definitions).
- **Affected code**: `core/frontend/src/components/` (new `CodeEditor` + theme module), `plugins/database-schema/frontend/src/components/SchemaEditorTab.tsx`, `plugins/apis/frontend/src/pages/ApiFormPage.tsx`.
- **Not affected**: `plugins/flows/frontend` (left as-is), persisted data/schema, backend parsing (`yaml.safe_load` paths), `ApiSpecDocViewer`/`OpenApiViewer`/`AsyncApiViewer` (read-only rendered documentation, a separate concern from raw-text editing).
