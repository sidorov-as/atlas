## 1. Shared code editor (core/frontend)

- [x] 1.1 Create `core/frontend/src/lib/codeEditorTheme.ts` by porting `defineFlowThemes`/`activeFlowTheme` from `plugins/flows/frontend/src/lib/monacoFlowTheme.ts` into generic `defineCodeEditorThemes`/`activeCodeEditorTheme` functions, same colors, no Flow-specific naming.
- [x] 1.2 Create `core/frontend/src/components/CodeEditorView.tsx`: the actual `@monaco-editor/react` `Editor` wrapper accepting `value`, `onChange`, `language: 'sql' | 'yaml' | 'json'`, optional `error`/`onValidate`-style prop for displaying a caller-supplied parse error, wired to the themes from 1.1.
- [x] 1.3 Create `core/frontend/src/components/CodeEditor.tsx`: a `lazy()`/`Suspense` wrapper around `CodeEditorView`, matching the shape of `core/frontend/src/components/DocumentationEditor.tsx`.
- [x] 1.4 Add/confirm `@monaco-editor/react` is a real (non-dangling) dependency of `core/frontend/package.json` now that it has a consumer.

## 2. Database schema SQL editor

- [x] 2.1 In `plugins/database-schema/frontend/src/components/SchemaEditorTab.tsx`, replace the `TextArea` for `sourceSql` with `CodeEditor` (`language="sql"`), preserving existing `value`/`onUpdate` wiring to `sourceSql`/`setSourceSql`.
- [x] 2.2 Verify the dialect `Select` (`DIALECT_OPTIONS`) is untouched and still only affects `databaseSchemaApi.create`/`.update` calls, not the editor's highlighting.
- [x] 2.3 Update/add tests in `SchemaEditorTab.test.tsx` to render the new editor and assert save/dialect behavior is unchanged.

## 3. API spec inline editor

- [x] 3.1 Add a small helper (e.g. `plugins/apis/frontend/src/lib/specFormat.ts`) exporting `detectSpecLanguage(content: string): 'json' | 'yaml'` (trimmed-leading-character sniff: `{`/`[` → `json`, else → `yaml`) and a `parseSpecContent(content: string)` wrapper around `js-yaml`'s `load()` returning a parse error message or `null`.
- [x] 3.2 In `plugins/apis/frontend/src/pages/ApiFormPage.tsx`, replace the inline `TextArea` (currently bound to `specContent`/`setSpecContent`) with `CodeEditor`, passing `language` from `detectSpecLanguage(specContent)`.
- [x] 3.3 Wire `parseSpecContent` to run on change (debounced if needed) and render a visible inline error (e.g. an `Alert`) when it returns a parse error, without blocking typing.
- [x] 3.4 Add/update tests covering: JSON content highlighted as JSON, YAML content highlighted as YAML, invalid content shows the inline error, valid content shows no error.

## 4. Verification

- [x] 4.1 Manually verify both editors in light and dark Gravity UI themes.
- [x] 4.2 Manually verify Flow's own editor (`plugins/flows/frontend`) is unchanged — same theme file, same behavior, not importing from `core/frontend`'s new modules.
- [x] 4.3 Run frontend test suites for `core/frontend`, `plugins/database-schema/frontend`, and `plugins/apis/frontend`.
