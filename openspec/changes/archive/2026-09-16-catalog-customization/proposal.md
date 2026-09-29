## Why

Atlas has no coherent way to customize a deployment's identity or homepage. `CatalogConfigurationController` only feeds the homepage's title/description from Django settings — the sidebar logo and title in `AppShell.tsx` are hardcoded and don't even read it. The homepage itself is otherwise a catalog-cards grid plus, today, the `atlas.c4` plugin's System Landscape diagram rendered unconditionally as a home widget — heavy, unrelated to "home," and with nowhere for an admin to add catalog-specific context. Settings has no admin gating at all beyond individual write endpoints, and has no room to grow beyond tag colors.

## What Changes

- Add `core/frontend/src/atlas.config.ts`, a hand-authored, EventCatalog-style file holding `title`, `tagline`, `logo`, `icon`. `AppShell.tsx`'s header and `HomePage.tsx` read it directly.
- **BREAKING**: Remove `CatalogConfigurationController`, `CatalogConfigurationOut`, the `catalog-configuration/` route, `CATALOG_TITLE`/`CATALOG_DESCRIPTION` settings, and the frontend's `catalogConfigurationApi`/`CatalogConfiguration` type. Catalog identity is no longer backend-configured.
- Move the System Landscape diagram off the homepage into its own `atlas.c4`-owned "System Map" nav item/route (positioned after "APIs," which requires no manifest change — `atlas.c4` already sits there in plugin order). Add an empty state ("System Map appears once your catalog has systems") when the catalog has zero Systems, replacing the earlier idea of a separate visibility toggle.
- Redesign the homepage: title/tagline (from `atlas.config.ts`) → a row of entity-kind counts (Systems/Components/APIs/Resources/Teams, from existing list endpoints) → an admin-editable "About this catalog" Markdown section.
- Add a `CatalogHomeSettings` singleton model holding that Markdown, seeded with Atlas-appropriate default content via a data migration (no manual seed step needed). Reads are open to any authenticated user; writes require `is_superuser`, matching the existing `TagWritePermission` pattern.
- Make Settings an admin-only area with nested routes (`/settings/home`, `/settings/tags`, `/settings` redirecting to `/settings/home`), gated by a new `GET /api/me/`-equivalent endpoint exposing `isAdmin` and a frontend `AdminProtected` guard. Move the existing tag-colors page under `/settings/tags`.

## Capabilities

### New Capabilities
- `catalog-branding`: Deployment identity (title, tagline, logo, icon) as a frontend-only config file consumed by the header and homepage, replacing the removed backend catalog-configuration endpoint.
- `catalog-home-content`: The homepage's post-identity content — entity-kind counts and an admin-editable "About this catalog" Markdown section backed by `CatalogHomeSettings`.
- `admin-settings-area`: Settings as an admin-only area — the `isAdmin` session-capability endpoint, the `AdminProtected` route guard, nav-item visibility, and nested `/settings/*` routing.

### Modified Capabilities
- `catalog-home-landscape`: Both existing requirements ("Configured catalog identity is displayed on the homepage" and "Homepage renders a catalog-wide System Landscape") are removed — identity moves to `catalog-branding`, the System Landscape moves to `c4-plugin`, and homepage content moves to `catalog-home-content`. This capability becomes empty and can be archived away once this change lands.
- `c4-plugin`: Adds a requirement that the System Landscape is presented as its own "System Map" nav destination (route + nav item owned by `atlas.c4`) rather than a homepage widget, including the zero-Systems empty state.
- `tag-management`: The admin tag-colors page moves from the flat `/settings` page to `/settings/tags` under the new nested Settings area; the admin-only write rule is unchanged, but page access itself now also requires `isAdmin` via `AdminProtected`.

## Impact

- **Frontend**: `core/frontend/src/atlas.config.ts` (new), `AppShell.tsx`, `HomePage.tsx`, `lib/entities.ts`, `lib/types.ts`, `lib/auth.ts`/`SessionContext.tsx` (new `isAdmin`), `components/Protected.tsx` (new `AdminProtected` sibling), `plugins/core/routes.ts` (settings route becomes `/settings/*`), new `SettingsLayout` + `/settings/home` + `/settings/tags` pages, `plugins/c4/frontend/src/index.ts` (`homeWidget` → `route`+`navItem`), new `plugins/c4/frontend/src/navItems.ts`.
- **Backend**: Remove `CatalogConfigurationController` and its schema/urls/settings/test. New `CatalogHomeSettings` model + migration (including a `RunPython` data migration seeding default content, per the `0007_reset_tag_colors.py` precedent) and its admin-gated API. New lightweight "who am I" endpoint exposing `isAdmin`.
- **Docs**: `docs-site/docs/configuration/` gains a section documenting `atlas.config.ts` as the only remaining way to set catalog branding.
- **No changes** to `distributions/default/manifest.yaml`, `ArchitectureRelationship`/diagram-render backend code, `NavItemContribution`'s shape (no nav sections), or `plugin-api` route/nav contracts.
