## Context

The catalog currently stores only `description`. It is shown beneath the page title and, depending on entity kind, as the entire Overview tab; Forms use a small plain textarea. The frontend already renders Markdown read-only with `react-markdown`, while the requested Gravity UI editor is not installed. API specification download is currently placed in Overview, while the OpenAPI/AsyncAPI viewer is in a `Documentation` tab.

System, Component, Resource, API, Group, and User inherit the shared `CatalogEntity` envelope. Flow is deliberately separate and has its own `description`, request schemas, and form. Ingestible entities are also written by YAML ingestion, so any new metadata field must be carried through both manual CRUD and ingestion.

## Goals / Non-Goals

**Goals:**

- Preserve concise summaries for headers, tables, previews, and search while providing full Markdown documentation.
- Make Markdown documentation editable in the requested Gravity UI editor on every manual entity and Flow form.
- Render full documentation in the natural reading position for entity and Flow detail pages.
- Make the API tab describe its actual content: a machine-readable specification rather than narrative documentation.

**Non-Goals:**

- Importing, transforming, or automatically generating existing descriptions into full documentation.
- Adding a visual viewer for gRPC, GraphQL, or new API-spec formats.
- Adding executable MDX/components, EventCatalog-style frontmatter, arbitrary HTML, or custom Markdown extensions.
- Editing YAML-managed entities in the web UI, or adding a form for Groups/Users.

## Decisions

### 1. Store one optional `documentation` Markdown string, not `long_descriptions` or `md_docs`

`documentation` is singular because every entity has one document and remains format-neutral at the domain/API boundary. The stored value is Markdown by contract, but its name does not bake in a storage syntax or promise a multi-document subsystem. `description` remains the concise, plain-summary field.

Add the field to the shared `CatalogEntity` envelope, so all envelope consumers get a stable metadata shape. The requested editable kinds are System, Component, Resource, API, and Flow; Groups/Users inherit the persisted/API metadata field but receive no new edit affordance.

Flow gets the same-named field directly because it does not inherit `CatalogEntity`.

### 2. Preserve existing summaries and initialise documentation empty

The data migration creates empty documentation for existing rows. Copying descriptions would duplicate text in the header and Overview, and attempting to derive a summary from Markdown would be lossy. Existing summary search therefore continues to work unchanged, while list search expands to include documentation for the ingestible kinds.

### 3. Use Gravity UI Markdown Editor only for authoring; retain `react-markdown` for read-only rendering

Create a reusable documentation-editor wrapper around `useMarkdownEditor` and `MarkdownEditorView`. It owns the editor instance, loads initial Markdown once per entity, obtains Markdown with `editor.getValue()`, and exposes it to the surrounding save flow. Configure it consistently with the app's UIKit language/theme setup and install the editor's required peer dependencies.

The read-only detail path remains the existing `react-markdown` component. It avoids shipping ProseMirror/CodeMirror to every detail page; the editor code is only loaded on create/edit routes. Markdown is rendered without raw HTML support.

### 4. Place full documentation in Overview, after Flow content

For System, Component, Resource, and API, Overview renders `metadata.documentation`; `description` is only the header summary. Component relationship summaries remain part of Overview after the documentation block unless the visual layout calls for a clearly separated related-information section.

Flow keeps the current graph and Steps sequence as the primary content; a `Documentation` section rendered from `flow.documentation` follows them. Its short description remains beneath the title.

### 5. API Specification is a content-specific tab

Rename the API tab from `Documentation` to `Specification`. When an API has stored spec content, the tab starts with the download action and stale-content label, then renders an OpenAPI or AsyncAPI viewer when supported. gRPC and GraphQL retain the tab/download action but show a clear unsupported-viewer message below it. Overview never contains API-spec controls.

## Risks / Trade-offs

- [Markdown editor bundle and peer dependencies increase edit-route weight] → lazy-load the editor wrapper and verify production build size and editor interaction in light/dark themes.
- [Hook-based editor is not a normal controlled input] → isolate lifecycle/value synchronisation in one wrapper and test edit/save/reopen flows.
- [Full documentation can make database search slower] → initially use the existing text-search mechanism with the extra field; measure before introducing full-text indexes.
- [YAML documentation can be malformed Markdown] → preserve source text and render safely without HTML; authors can correct it in the source repository.
- [No gRPC/GraphQL viewer] → retain download access and name the limitation explicitly rather than misleadingly hiding a stored specification.

## Migration Plan

1. Add nullable/default-empty documentation fields via a Django migration for the shared envelope tables and Flow; deploy without modifying current descriptions.
2. Extend schemas, serializers, ingestion/upsert, and frontend types so old clients may omit documentation and receive an empty string.
3. Release form editor and detail rendering, then update demo seed data/YAML fixtures with representative Markdown as desired.
4. Roll back application code safely while retaining the additive database columns; no destructive data migration is needed.

## Open Questions

- None blocking. The scope intentionally includes a Specification tab for gRPC/GraphQL when spec content exists, with download-only fallback.
