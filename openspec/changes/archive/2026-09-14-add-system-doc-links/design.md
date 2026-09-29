## Context

`CatalogEntity.links` is a JSON metadata array shared by all entity kinds.
It currently contains `{url, title, type}`, is accepted by the common API
schemas, and is fully overwritten by YAML ingestion. The System Docs tab and
detail right rail render that array as an unstructured list; the manual System
form omits it. The Systems list uses the shared `EntityListPage` preview panel,
which has no kind-specific content extension or URL-addressable detail tab.

The change is limited to Systems as the first consumer. The metadata contract
remains common so existing and future entity kinds retain a compatible link
shape.

## Goals / Non-Goals

**Goals:**

- Make System links useful as a browseable, searchable document/resource
  catalog with title, description, URL, and optional type.
- Preserve a single source for the complete link list: manual edit for manual
  Systems or YAML ingestion for YAML-managed Systems, never a mixture.
- Use one paginated read API for both the complete Docs tab and the bounded
  Systems-list preview.
- Make the Docs tab directly linkable from the Systems list.

**Non-Goals:**

- Creating a separate relational Document or Link model, per-link ownership,
  permissions, history, or independent CRUD endpoints.
- Categorization/filtering by `type`, link health checks, URL previews, or
  importing content from linked sites.
- Changing the Docs UX for Component, Resource, API, Team, or User pages.

## Decisions

### 1. Extend common metadata links rather than introduce a new model

`LinkSchema` gains `description: str = ""`; existing `{url, title, type}`
values remain valid. `CatalogEntity.links` stays a JSON array, so no database
migration is required. The System-specific read endpoint materializes this
array as paginated rows.

This keeps the entity-level provenance rule intact: Entity Service manual
writes remain blocked for any YAML-managed System, while ingestion continues
to replace the entire metadata payload. A separate link table would require
per-row provenance and reconciliation rules that conflict with this simple,
already-enforced boundary.

### 2. Provide a dedicated read-only System document-links endpoint

`GET /api/systems/{id}/docs/` accepts `q`, `page`, and `page_size`, returns the
standard paginated envelope, and requires the same authenticated read access
as System retrieval. `q` is a case-insensitive substring match over `title`
and `description`; URL and type are not search fields. Results retain the
declaration order in `metadata.links`, which makes YAML ordering and manual
editing order visible and deterministic.

Pagination happens after filtering. Invalid page input follows the repository's
existing pagination conventions. The endpoint has no write methods; manual
mutations continue through the existing System PATCH route with the complete
`metadata.links` array.

### 3. Make the Docs tab the full browser and manager, and the list aside a bounded consumer

The Docs tab requests the endpoint with a default page size of 20, keeps its
search and page in URL query parameters, and renders `Title`, `Description`,
and `Link` columns. Link contains icon-only external-open and copy controls;
the copy icon changes from `Copy` to `CopyCheck` after successful copying and
reports failure visibly. Each row also uses the standard `g-table__actions`
area for Edit and Remove.

For a manual System, an Add button sits beside the search field and opens the
same modal used for edit. The modal collects title, optional description, URL,
and optional type; it validates a non-empty, unique URL. Add, edit, and remove
each update the complete ordered link array through the existing System PATCH
route, then reload the current Docs page. YAML-managed Systems show neither
the Add button nor row mutation actions. The System create/edit form
intentionally has no link editor.

The System preview panel requests the same endpoint lazily only after that
System is selected, with `page_size=5`. It shows no Documentation section when
the count is zero. When `count > 5`, it renders `More (count)`, which navigates
to `/systems/{id}?tab=docs`. The preview does not preload or rely on each
System list row's full `metadata.links` payload.

### 4. Add a narrow preview extension point and URL tab selection

`EntityListPage`/`EntityPreviewPanel` receive an optional render prop for a
kind-specific preview section. `SystemsListPage` alone supplies the document
preview; the generic panel keeps ownership of title, About, Description,
open, and close controls.

`EntityDetailShell` reads a `tab` URL query parameter when it names an
applicable contribution, updates it when the user selects a tab, and falls
back to the first applicable tab for an absent or invalid parameter. This
makes the More link shareable without special System routing.

### 5. Docs-tab editing writes the complete list

The Docs tab is the sole manual editing surface for System links. Its modal
and row actions submit a complete ordered `metadata.links` list through the
existing PATCH route. This preserves entity-level provenance and validation
without putting document-link controls on the System create/edit form.

## Risks / Trade-offs

- [JSON-array links cannot be queried efficiently across the entire catalog]
  → The endpoint reads one System's bounded metadata array, so this is not a
  catalog-wide query. A future cross-System document search can introduce a
  dedicated projection if needed.
- [Clipboard API can be unavailable or denied] → Surface an inline error and
  leave the Open action available; do not silently claim a successful copy.
- [Changing tab selection can affect existing detail deep links] → Invalid or
  inapplicable `tab` values fall back safely to the existing first-tab behavior.
- [A new common schema field may be ignored by older clients] → Default an
  omitted description to `""`, preserving old YAML and API clients.

## Migration Plan

1. Deploy the backward-compatible schema/API/frontend changes together; old
   persisted links and manifests remain valid without transformation.
2. Update the `catalog-info.yaml` reference with optional `description`.
3. Roll back application code if needed; persisted `description` keys remain
   harmless JSON data and are ignored by the prior schema/UI.

## Open Questions

- None. The preview cap is fixed at five links for this change; it can become a
  configuration setting only after real usage establishes a need.
