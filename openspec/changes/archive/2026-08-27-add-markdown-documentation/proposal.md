## Why

`description` currently carries two incompatible responsibilities: a compact summary in page headers, lists, and search, and the entire content of an entity's Overview. That prevents rich, structured documentation while making concise catalog navigation harder to preserve.

## What Changes

- Add an optional Markdown `documentation` field alongside the existing short `description` for System, Component, Resource, API, and Flow.
- Render an entity's Markdown documentation in the Overview tab; retain `description` as the summary in headers, lists, previews, and search results.
- Add a Gravity UI Markdown editor to manual create/edit forms after the entity's standard and kind-specific fields.
- Show a Flow's Markdown documentation below its graph and Steps section.
- Rename the API `Documentation` tab to `Specification`, move the download action into it, and show the available OpenAPI or AsyncAPI viewer directly below the action.
- For a gRPC or GraphQL API with stored specification content, show the `Specification` tab and download action with an explicit unsupported-viewer state.
- Keep existing descriptions unchanged and initialise documentation as empty; do not duplicate old summaries into the new field.

## Capabilities

### New Capabilities

- `markdown-entity-documentation`: Markdown authoring and rendering for the full documentation of catalog entities and Flows.

### Modified Capabilities

- `entity-catalog`: Extend the entity metadata envelope and searchable fields with full Markdown documentation.
- `catalog-web-ui`: Change Overview/form behavior and API specification-tab terminology and placement.
- `flow-management`: Persist, edit, and render a Flow's full Markdown documentation after its graph and steps.

## Impact

- Backend models, migrations, Pydantic request/response schemas, list filtering, CRUD, and YAML ingestion for ingestible entity documentation; Flow's separate model and API contract also change.
- Frontend entity types, form shells, all relevant forms/detail pages, and API detail tests change.
- `@gravity-ui/markdown-editor` and its peer dependencies are added for edit-only authoring; the existing lightweight `react-markdown` renderer remains the read-only renderer.
