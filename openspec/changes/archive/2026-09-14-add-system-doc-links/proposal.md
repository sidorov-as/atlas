## Why

Systems can already carry generic `metadata.links`, including links ingested from
`catalog-info.yaml`, but the Docs tab only renders an unsearchable list. Users
need one reliable, source-aware Docs-tab workflow to catalog and maintain
place to catalog operational documentation such as wikis, dashboards,
whiteboards, runbooks, and other external resources.

## What Changes

- Extend a metadata link with an optional per-link description while preserving
  the existing URL, title, and type fields.
- Add a read-only, paginated System document-links API with case-insensitive
  search across link title and description.
- Replace the System Docs tab's plain list with a searchable, paginated table
  with compact Link actions and Edit/Remove table actions.
- Let manual Systems add and edit document links from the Docs tab through a
  modal; YAML-managed Systems remain read-only and continue to receive their
  complete link list solely from `catalog-info.yaml` ingestion.
- Add a limited Documentation section to the selected System preview panel on
  `/systems`; it shows the first five links and links to that System's Docs tab
  when more links exist.
- Support a URL-selected detail tab so the preview's More action can open the
  target System directly on its Docs tab.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `entity-catalog`: extend the common metadata-link contract and expose a
  paginated, searchable System document-links read API.
- `catalog-ingestion`: ingest and reconcile per-link descriptions as part of a
  YAML-managed entity's complete metadata.
- `catalog-web-ui`: provide the System Docs table and modal link manager, and
  capped documentation preview in the Systems list aside.
- `entity-detail-shell`: allow a canonical detail URL to select an applicable
  contributed tab.

## Impact

- Shared plugin API schemas, core entity metadata serialization, and the
  Standard Catalog System REST API gain the document-link contract and list
  endpoint.
- Ingestion, its manifest documentation, and fixtures/tests gain link
  descriptions and full-overwrite coverage.
- The Standard Catalog frontend, shared entity list preview extension point,
  and EntityDetailShell gain the Docs table, modal link manager, preview section, and
  deep-link handling.
