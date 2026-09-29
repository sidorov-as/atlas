## Context

Two editors currently use a plain Gravity UI `TextArea` for structured text with no highlighting: `SchemaEditorTab` (raw SQL) and `ApiFormPage`'s inline spec field (OpenAPI/AsyncAPI YAML-or-JSON). Flow already solved highlighting for its own JSON editing needs using `@monaco-editor/react`, but entirely inside `plugins/flows/frontend` — theme definitions (`monacoFlowTheme.ts`), language config, and validation wiring are all plugin-local. `core/frontend` already lists `@monaco-editor/react` as a dependency but has no component using it, and the codebase's existing precedent for cross-plugin UI reuse (`core/frontend/src/components/RefSelect.tsx`, consumed by core and `plugins/flows`) puts shared components in `core/frontend`, since plugins may not import each other directly (`core-plugin-contract-surface`).

`spec_content` (the API spec editor's target field) has no stored format discriminator — it's a plain `TextField`, and both the backend (`yaml.safe_load`) and the frontend doc viewer (`js-yaml`'s `load()`) already parse it through one YAML-or-JSON-tolerant path. Any format detection needed for choosing a Monaco language mode has to happen client-side, from content alone.

## Goals / Non-Goals

**Goals:**
- One reusable, theme-aware Monaco wrapper in `core/frontend` that any plugin can drop in for `sql`/`yaml`/`json` highlighting.
- `SchemaEditorTab` and `ApiFormPage` adopt it, replacing their `TextArea` inputs.
- The API spec editor auto-selects `yaml` or `json` highlighting from content and shows a visible parse error for invalid content before save.

**Non-Goals:**
- Migrating Flow's own editor onto the new shared component (left untouched; candidate follow-up).
- SQL dialect-aware grammar/highlighting (Postgres vs. MySQL vs. MSSQL keywords) — generic `sql` tokenization only.
- Autocomplete, schema-aware (e.g. OpenAPI-schema-driven) validation, or any change to persisted data or backend parsing.

## Decisions

### 1. The shared `CodeEditor` is a thin, generic wrapper — no business rules inside it

`core/frontend/src/components/CodeEditor.tsx` takes `value`, `onChange`, `language: 'sql' | 'yaml' | 'json'`, and an optional `onValidate`/error-display hook. It knows nothing about API specs, dialects, or Atlas domain concepts — same posture as `RefSelect`, which is generic over "kind + query", not aware of Flow specifically. Format-sniffing (YAML vs. JSON) and any spec-specific behavior stay in `plugins/apis/frontend`, keeping the shared component reusable by future callers (e.g. a `graphql`/`grpc` spec editor later) without modification.

Alternative considered: bake a `'spec' | 'sql'` mode into the component that internally sniffs format. Rejected — it would leak apis-plugin-specific assumptions (what "spec" text looks like) into a core component other plugins must also depend on.

### 2. Extract and generalize the theme; leave Flow's copy in place

`plugins/flows/frontend/src/lib/monacoFlowTheme.ts`'s theme-definition and active-theme-detection logic (`defineFlowThemes`, `activeFlowTheme`) is ported into a new `core/frontend/src/lib/codeEditorTheme.ts` with generic naming (e.g. `defineCodeEditorThemes`, `activeCodeEditorTheme`), same colors. Flow's own file is left as-is rather than refactored to import the new module, per the proposal's explicit non-goal of touching Flow in this change.

This accepts short-term duplication between the two theme files (see Risks) in exchange for zero behavioral risk to Flow's editor, which the proposal deliberately keeps out of scope.

### 3. Validity checking uses `js-yaml`, not Monaco's own per-language diagnostics

Monaco has rich built-in diagnostics for `language="json"` (as Flow already uses via `monaco.languages.json.jsonDefaults`), but no built-in YAML linting — that requires the separate `monaco-yaml` package, which isn't installed and isn't proposed here. Since the spec editor's content can be either format, relying on Monaco's own validation would give JSON real diagnostics and YAML none — an inconsistent experience depending on what the author happens to paste.

Instead, `ApiFormPage` validates content itself by attempting `js-yaml`'s `load()` (already used by `ApiSpecDocViewer` for the same YAML-or-JSON-tolerant parsing) on change, independent of whichever Monaco language is active for highlighting, and passes the resulting error (or `null`) to the shared component for display. One validation code path, consistent for both formats.

### 4. Format detection is a leading-character sniff, decoupled from parsing

`plugins/apis/frontend` gets a small helper — `detectSpecLanguage(content): 'json' | 'yaml'` — that inspects `content.trim()`'s first character (`{` or `[` → `json`, otherwise → `yaml`) purely to choose Monaco's tokenizer. It does not gate or affect the `js-yaml` validity check from Decision 3, which parses the same way regardless of the guessed language. A misdetection only produces cosmetically-off highlighting, never a false validity result.

### 5. Lazy-load the editor, matching `DocumentationEditor`'s existing pattern

`CodeEditor` is loaded via `lazy()`/`Suspense`, the same shape already used by `core/frontend/src/components/DocumentationEditor.tsx` for its heavy Markdown view, so routes/pages that don't render an editor don't pay Monaco's bundle cost.

## Risks / Trade-offs

- **Theme duplication between `plugins/flows/frontend/src/lib/monacoFlowTheme.ts` and the new `core/frontend/src/lib/codeEditorTheme.ts`** → Mitigation: colors are copied identically at introduction so both render the same; documented in Open Questions as a follow-up to collapse once/if Flow migrates.
- **Leading-character format sniffing can misdetect** (e.g. a YAML document using flow-style mapping syntax starting with `{`) → Mitigation: sniffing only selects the Monaco tokenizer for highlighting, not the validity check (Decision 3 parses with `js-yaml` regardless), so a misdetection is cosmetic, not a functional or data bug.
- **No SQL dialect-specific highlighting** → users selecting MySQL or MSSQL still see generic SQL tokenization; this is an explicit non-goal, not a defect, but worth calling out in review so it isn't mistaken for an oversight.
- **Monaco bundle weight** added to two more plugin bundles → Mitigation: lazy-loaded per Decision 5, consistent with the existing `DocumentationEditor` precedent.

## Open Questions

- Should Flow's own JSON editor eventually migrate onto the shared `CodeEditor` (retiring its private theme file)? Not decided here — left as a candidate follow-up change.
- Is generic SQL highlighting sufficient long-term, or will dialect-aware highlighting (custom Monarch tokenizer per `DIALECT_OPTIONS` value) become a follow-up ask once this ships?
