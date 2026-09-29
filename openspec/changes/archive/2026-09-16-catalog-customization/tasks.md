## 1. Backend: CatalogHomeSettings (About this catalog)

- [x] 1.1 Add `CatalogHomeSettings` model (singleton row) in `core/backend/server/apps/catalog/models/` and register it in `models/__init__.py`
- [x] 1.2 Add its schema migration
- [x] 1.3 Add a `RunPython` data migration seeding the default Atlas Markdown content, following the pattern in `core/backend/server/apps/catalog/migrations/0007_reset_tag_colors.py`
- [x] 1.4 Add `GET`/`PATCH` API for `CatalogHomeSettings`: `GET` open to any authenticated user, `PATCH` gated by an `is_superuser` check matching `TagWritePermission.check_write` in `core/backend/server/apps/catalog/api/permissions.py`
- [x] 1.5 Add schema/urls entries and wire the controller
- [x] 1.6 Add backend tests: default content present after migration alone (no seed command), read allowed for any authenticated user, write rejected for non-superuser, write accepted for superuser

## 2. Backend: admin-status endpoint

- [x] 2.1 Add a small endpoint (e.g. `GET /api/me/`) returning `{isAdmin: bool}` for the current authenticated user, independent of django-allauth's own session payload
- [x] 2.2 Add tests: unauthenticated request rejected, authenticated non-superuser gets `isAdmin: false`, superuser gets `isAdmin: true`

## 3. Backend: remove CatalogConfigurationController

- [x] 3.1 Remove `CatalogConfigurationController` and `CatalogConfigurationOut` from `core/backend/server/apps/catalog/api/views.py` / `schemas.py`
- [x] 3.2 Remove the `catalog-configuration/` route from `core/backend/server/apps/catalog/api/urls.py`
- [x] 3.3 Remove `CATALOG_TITLE`/`CATALOG_DESCRIPTION` from `core/backend/server/settings/components/common.py`
- [x] 3.4 Delete `core/backend/server/apps/catalog/tests/test_catalog_configuration.py`

## 4. Frontend: catalog branding config

- [x] 4.1 Add `core/frontend/src/atlas.config.ts` exporting `{ title, tagline, logo, icon }`
- [x] 4.2 Update `AppShell.tsx` to read the sidebar logo/title from `atlas.config.ts` instead of hardcoded literals
- [x] 4.3 Remove `catalogConfigurationApi` from `core/frontend/src/lib/entities.ts` and `CatalogConfiguration` from `core/frontend/src/lib/types.ts`
- [x] 4.4 Update any existing tests referencing `catalogConfigurationApi`/`CatalogConfiguration` (e.g. `HomePage.test.tsx`)

## 5. Frontend: System Map (atlas.c4)

- [x] 5.1 Add `plugins/c4/frontend/src/navItems.ts` contributing a "System Map" `navItem` + its `route`
- [x] 5.2 Remove the `homeWidget` contribution from `plugins/c4/frontend/src/index.ts`; add the new route/navItem contributions
- [x] 5.3 Turn `SystemLandscapeWidget.tsx` into (or wrap it with) the System Map page body, reusing `DiagramViewer` + `systemLandscapeUrl()` as-is
- [x] 5.4 Add the zero-Systems empty state: check `systemsApi.list()`'s count and show a message ("System Map appears once your catalog has systems.") instead of the diagram when it's 0 — no CTA button
- [x] 5.5 Update/add frontend tests: `SystemLandscapeWidget.test.tsx` → move/rename to cover the new page, plus the empty-state case

## 6. Frontend: Homepage content

- [x] 6.1 Rebuild `HomePage.tsx`: title/tagline from `atlas.config.ts` (remove the `catalogConfigurationApi` fetch and its loading/error states) → entity-kind counts row (Systems/Components/APIs/Resources/Teams via existing list endpoints) → "About this catalog" section
- [x] 6.2 Render "About this catalog" using the existing `MarkdownDescription.tsx` component against the new `CatalogHomeSettings` API
- [x] 6.3 Keep `composedContributions.homeWidgets` rendering in place (now empty, since the c4 widget moved) — do not remove the extension point
- [x] 6.4 Update `HomePage.test.tsx` for the new layout and data sources

## 7. Frontend: admin-gated, nested Settings

- [x] 7.1 Expose `isAdmin` on the frontend: extend session handling (`core/frontend/src/lib/auth.ts` / `SessionContext.tsx`) to also fetch the new admin-status endpoint
- [x] 7.2 Add `AdminProtected`, a sibling to `core/frontend/src/components/Protected.tsx`, redirecting non-admins away from `/settings/*`
- [x] 7.3 Hide the "Settings" nav item for non-admins
- [x] 7.4 Change the settings route in `core/frontend/src/plugins/core/routes.ts` to `route({ id: 'atlas.core.settings', path: '/settings/*', component: SettingsLayout })`
- [x] 7.5 Build `SettingsLayout` with a left sub-navigation (use the `/gravity-ui` skill to pick the right Gravity UI primitive) and internal `<Routes>` for `/settings/home` and `/settings/tags`, with `/settings` redirecting to `/settings/home`
- [x] 7.6 Add `/settings/home`: the `CatalogHomeSettings` editor, reusing `DocumentationEditorView.tsx`'s `MarkdownEditorView`/`useMarkdownEditor`
- [x] 7.7 Move the existing tag-color table (currently `SettingsPage.tsx`) to `/settings/tags`
- [x] 7.8 Update/add tests: admin sees Settings nav + can open every section, non-admin is redirected from `/settings/*` and doesn't see the nav item, each nested route renders its own section directly

## 8. Docs

- [x] 8.1 Document `atlas.config.ts` in `docs-site/docs/configuration/` as the way to set catalog branding, replacing any mention of `CATALOG_TITLE`/`CATALOG_DESCRIPTION`
- [x] 8.2 Note the breaking change (removed backend catalog-configuration endpoint/env vars) in the appropriate docs-site section (deployment/upgrade notes)

## 9. Cleanup / verification

- [x] 9.1 Run the full backend and frontend test suites
- [x] 9.2 Confirm `distributions/default/manifest.yaml` needs no change (verify "System Map" lands after "APIs" purely from existing plugin order)
- [x] 9.3 Manually verify in a browser: header branding, homepage counts + About section (as both admin and non-admin), System Map page (with and without Systems in the catalog), Settings admin gating and nested routing
