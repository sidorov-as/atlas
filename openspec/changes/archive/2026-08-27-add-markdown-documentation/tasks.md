## 1. Data model and API contracts

- [x] 1.1 Add default-empty `documentation` storage to the shared catalog envelope and Flow, and generate a non-destructive Django migration for all affected concrete tables.
- [x] 1.2 Extend metadata and Flow create/patch/output schemas, serializers, CRUD application helpers, and frontend API types/inputs to round-trip documentation while accepting omitted values.
- [x] 1.3 Update ingestion metadata validation and upsert so YAML-managed System, Component, Resource, and API entities preserve `metadata.documentation`.
- [x] 1.4 Extend ingestible entity list search to match `documentation` in addition to name and short description.
- [x] 1.5 Update representative seed data and YAML fixtures with Markdown documentation where it improves demo coverage without changing existing summaries.

## 2. Markdown authoring UI

- [x] 2.1 Add `@gravity-ui/markdown-editor` and its required peer dependencies, configure its language/theme integration, and confirm a production build succeeds.
- [x] 2.2 Build a reusable, lazily loaded Documentation editor wrapper that initialises from persisted Markdown and provides the current `editor.getValue()` to form save handlers.
- [x] 2.3 Extend `EntityFormShell` and System/Component/Resource/API forms so the editor appears after all standard and kind-specific fields and submits `metadata.documentation`.
- [x] 2.4 Extend `FlowFormPage` to initialise, edit, and submit `documentation` without disrupting the Monaco steps editor or live graph preview.

## 3. Detail-page rendering and API specifications

- [x] 3.1 Render `metadata.documentation` through the existing safe Markdown renderer in System, Component, Resource, and API Overview tabs; keep `description` exclusively as the header/list/preview summary.
- [x] 3.2 Render Flow Markdown documentation in a labeled section below its graph and Steps, with an explicit empty state.
- [x] 3.3 Rename the API `Documentation` tab to `Specification`, remove download controls from Overview, and place download/staleness status before the specification content.
- [x] 3.4 Show embedded viewers below the Specification action for OpenAPI/AsyncAPI and a clear download-only unsupported-viewer state for gRPC/GraphQL content.

## 4. Verification

- [x] 4.1 Add backend tests for documentation defaults, manual create/patch/read, YAML ingestion/upsert, Flow updates, and documentation-inclusive list search.
- [x] 4.2 Add frontend tests for documentation field submission, rendered Overview/Flow placement, API Specification naming/order, and gRPC/GraphQL fallback.
- [x] 4.3 Run targeted backend and frontend test suites, Django migration checks, frontend typecheck/build, and repository linting; resolve all regressions.
