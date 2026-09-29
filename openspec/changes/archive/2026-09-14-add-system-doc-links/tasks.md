## 1. Shared contract and System document-links API

- [x] 1.1 Extend the shared LinkSchema, metadata serializers, and frontend link types with the backward-compatible `description` field.
- [x] 1.2 Add the read-only `GET /api/systems/{id}/docs/` route, query schema, paginated response schema, and System view implementation.
- [x] 1.3 Implement case-insensitive title/description filtering, declared-order pagination, and standard not-found/auth behavior for the document-links endpoint.
- [x] 1.4 Add backend unit/API tests for legacy links without descriptions, described link serialization, search, pagination, ordering, and rejected write methods.

## 2. YAML ingestion and documentation

- [x] 2.1 Verify the ingestion intent and full-overwrite path preserve link descriptions without weakening YAML-managed write protection.
- [x] 2.2 Add ingestion tests for described links and removal of a link on re-ingestion.
- [x] 2.3 Update the `catalog-info.yaml` reference and examples to document optional link descriptions and supported resource-link uses.

## 3. System form scope

- [x] 3.1 Keep System create/edit forms free of a document-link editor and do not submit `metadata.links` from those forms.

## 4. System Docs browser

- [x] 4.1 Add the frontend document-links API client and paginated document-link types.
- [x] 4.2 Replace the System Docs tab's plain list with a URL-backed search field, paginated table, and empty/loading/error states.
- [x] 4.3 Add the manual-System Add button and shared create/edit modal; save complete ordered links through System PATCH and hide mutation controls for YAML-managed Systems.
- [x] 4.4 Replace Open/Copy columns with a Link icon column (`ArrowUpRightFromSquare`, `Copy` → `CopyCheck`) and add Edit/Remove `g-table__actions`.
- [x] 4.5 Add Docs-tab tests for search/page URL state, rendering, empty state, pagination, link actions and copy outcomes, modal add/edit/remove flows, PATCH payload order, and YAML-managed read-only state.

## 5. Systems-list documentation preview and deep links

- [x] 5.1 Add a narrow optional preview-section render extension to the shared EntityListPage/EntityPreviewPanel without changing other entity list pages.
- [x] 5.2 Implement the System Documentation preview section with lazy `page_size=5` loading, no empty section, external link actions, and `More (count)`.
- [x] 5.3 Make EntityDetailShell synchronize an applicable `tab` query parameter with its active tab and safely fall back for absent/invalid values.
- [x] 5.4 Wire `More (count)` to `/systems/{id}?tab=docs` and add frontend tests for the preview cap, lazy load, More navigation, and direct Docs deep links.

## 6. Verification

- [x] 6.1 Run affected backend tests, frontend tests, type checks, and lint/format checks; fix any regressions.
- [x] 6.2 Validate the OpenSpec change with `openspec validate add-system-doc-links --strict`.
