## Context

Today, catalog identity is split and inconsistent: `CatalogConfigurationController` (`core/backend/server/apps/catalog/api/views.py`) exposes `CATALOG_TITLE`/`CATALOG_DESCRIPTION` (Django settings, env-backed) via `GET /api/catalog-configuration/`, consumed only by `HomePage.tsx`. `AppShell.tsx`'s sidebar logo/title are hardcoded literals and never call that endpoint. There is no logo/icon configuration at all. The homepage is a catalog-cards grid plus, unconditionally, the `atlas.c4` plugin's System Landscape diagram (`homeWidget` contribution in `plugins/c4/frontend/src/index.ts`) — heavy and unrelated to "home." Settings (`SettingsPage.tsx`) has no page-level access control; only its tag-color write endpoint checks `request.user.is_superuser` (`TagWritePermission.check_write`).

This design was produced through an extended exploration that read the actual models, endpoints, and components involved (not assumed) — each decision below states what was verified.

## Goals / Non-Goals

**Goals:**
- One coherent, discoverable way to set deployment branding (title, tagline, logo, icon).
- A homepage that shows real, truthful data — nothing fabricated for a mockup that doesn't match Atlas's actual data model.
- Move the System Landscape diagram to a dedicated destination without touching its rendering backend.
- A real admin area in Settings, with room to grow beyond tag colors, properly access-gated both in the UI and at the API.

**Non-Goals:**
- Per-distribution override of `atlas.config.ts` without forking Core's frontend source. Verified gap: `distributions/*/manifest.yaml` has zero notion of branding today, and Core is meant to be an independently versioned, distributable package (ADR 0025) — an external operator building their own distribution has no source file to hand-edit. Explicitly deferred; `atlas.config.ts` is a plain committed file for now (YAGNI).
- A generic nav-section/grouping mechanism ("Observability" or otherwise). `NavItemContribution` stays flat; nav order continues to be plugin order.
- A filterable/projection diagram builder. Separate future change; likely lands as an entity-detail tab on Systems (alongside the existing `SystemContextTab`/`SystemArchitectureTab`), not a new nav destination.
- Any Home widget whose backing data doesn't exist in Atlas today: "Service health" (no health-check integration anywhere in the codebase), "Lifecycle" stage distribution (`CatalogEntity.status` only has `active`/`removed` — no environment/stage field), "Top domains" (no `Domain` entity kind exists; kinds are `system`/`component`/`resource`/`api`/`group`/`user`). Also explicitly excluded despite being real, buildable, and grounded in existing data (`EntityAuditRecord`, `Relation`): "Recently updated" and "Most connected" — rejected on preference, not feasibility.
- MDX or any embed syntax inside the "About this catalog" Markdown. Plain Markdown only, via the existing `@gravity-ui/markdown-editor` stack.

## Decisions

### 1. Branding lives in a committed frontend file, not a backend endpoint or DB table
`core/frontend/src/atlas.config.ts` exports `{ title, tagline, logo, icon }`. `AppShell.tsx` imports it directly for the sidebar logo/text (replacing its hardcoded literals); `HomePage.tsx` imports it for title/tagline (replacing the `catalogConfigurationApi.get()` call, its `useAsync`/`Loader`/`Alert` states, and the whole loading round-trip).

Alternatives considered:
- **DB-backed settings table**: rejected — branding is deploy-time identity, not something that needs runtime editing without a rebuild, and it would need its own admin CRUD UI for no real benefit over a file.
- **Build-time env vars (`import.meta.env.VITE_*`)**: would keep the file distribution-overridable without forking Core, at the cost of indirection. Rejected for now given the Non-Goal above; revisit if/when external distributions become real.

Consequence: `CatalogConfigurationController`, `CatalogConfigurationOut`, the `catalog-configuration/` URL, `CATALOG_TITLE`/`CATALOG_DESCRIPTION` settings, and `test_catalog_configuration.py` are deleted outright, not deprecated. `catalogConfigurationApi`/`CatalogConfiguration` (frontend) are deleted too. This is a **breaking** change for anyone who set those env vars.

### 2. System Landscape becomes `atlas.c4`'s own nav destination, not a Home widget
`plugins/c4/frontend/src/index.ts` drops the `homeWidget({ id: 'atlas.c4.home.system-landscape', ... })` contribution and adds `route()` + `navItem()` contributions (its first — `navItems.ts` doesn't exist yet in this plugin). The existing `SystemLandscapeWidget.tsx` (already self-contained: `DiagramViewer` + `systemLandscapeUrl()`, no Home-specific logic) becomes the route's page body essentially unchanged.

Verified: nav order follows plugin order in `installedFrontendPlugins`, generated from `distributions/default/manifest.yaml`'s `plugins:` order (`standard-catalog → apis → c4 → database-schema → ingestion → flows`). `atlas.c4` already sits directly after `atlas.apis`, so "System Map after APIs" requires **no manifest change**.

No backend change: `ArchitectureRelationship`, `build_system_landscape()`, and the diagram-render endpoint in `plugins/c4/backend` are untouched.

**Empty state, not a visibility flag**: Verified `build_system_landscape()` (`plugins/c4/backend/atlas_plugin_c4/c4.py`) always renders every System entity as a node, with or without relationships ("Systems are always present" — isolated nodes are a normal render, not an empty one). The real empty condition is zero Systems in the catalog. The System Map page checks the existing `systemsApi.list()` pagination count (no new backend endpoint) and shows an empty-state message ("System Map appears once your catalog has systems," no CTA button) instead of the diagram when that count is 0. This replaces the originally-discussed per-deployment "hide this feature" toggle — moving the diagram off Home already resolves the "it's heavy, don't load it on every visit" concern that motivated the toggle.

### 3. Homepage content: counts (existing data) + admin Markdown (new, deliberately narrow)
Counts row: one request per kind's existing paginated list endpoint (`systemsApi.list`, etc.), reading the pagination total — no new backend surface.

"About this catalog": a new `CatalogHomeSettings` Django model — a singleton row (the codebase has no existing singleton-model convention to follow exactly; use a fixed, well-known primary key with a `get_or_create`-style accessor, kept as simple as `Tag` is). Seeded via a `RunPython` data migration, following the exact precedent at `core/backend/server/apps/catalog/migrations/0007_reset_tag_colors.py` — no manual seed command needed for a fresh deployment to have real content.

Read/write split mirrors the already-established asymmetric pattern for `Tag.color`: `GET` open to any authenticated user (the content is shown to everyone on Home), `PATCH`/write requires `request.user.is_superuser`, implemented the same way as `TagWritePermission.check_write`.

Rendering/editing reuse existing components verbatim: `MarkdownDescription.tsx` for display, `DocumentationEditorView.tsx`'s `MarkdownEditorView`/`useMarkdownEditor` (`@gravity-ui/markdown-editor`) for the admin editor — no new markdown library or embed DSL.

Default seed content is adapted from a Backstage-style "Welcome" block to only reference real Atlas capabilities (manual registration, `catalog-info.yaml` ingestion, per-entity documentation tabs) and real links (the actual `docs-site` at `sidorov-as.github.io/atlas`), not invented features (no software-templates/scaffolding equivalent exists in Atlas).

The existing `homeWidget` extension point stays wired into `HomePage.tsx` (`composedContributions.homeWidgets`) but ships empty — it's proven infrastructure (this is exactly how System Landscape worked before), just unused until/unless a future change populates it.

### 4. Settings becomes an admin-gated area with nested routing
**Admin signal**: today the frontend has no way to know `is_superuser` — session state comes from django-allauth headless (`/_allauth/browser/v1/auth/session`), whose user payload (`SessionUser` in `core/frontend/src/lib/auth.ts`) is `{id, display, username}` only, an allauth-owned shape. Add a small, separate Atlas-owned endpoint (naming TBD, e.g. `GET /api/me/`) returning at least `{isAdmin: bool}`, rather than customizing allauth's `HEADLESS_ADAPTER`/user serializer. This keeps admin-signal plumbing out of the `auth-provider-extension` surface, which is scoped to authentication providers, not authorization roles.

**Two independent layers, not one**: the real security boundary is each settings-owned write endpoint requiring `is_superuser` server-side (already true for tags; true for `CatalogHomeSettings` per Decision 3). A new `AdminProtected` route-layout component (sibling to the existing `Protected` in `core/frontend/src/components/Protected.tsx`, which already wraps every non-public route with the session check + `AppShell`) additionally checks `isAdmin` and redirects a non-admin away from `/settings/*` — this is a UX guard against a dead-end UI, not itself the security boundary. The "Settings" nav item is also hidden from non-admins once `isAdmin` is known.

**Nested routes, no `plugin-api` changes**: a single `route({ id: 'atlas.core.settings', path: '/settings/*', component: SettingsLayout })` in `core/frontend/src/plugins/core/routes.ts`. `SettingsLayout` owns its own left sub-navigation (Home, Tag colors, room for more) and an internal `<Routes>` for `/settings/home` (new `CatalogHomeSettings` editor) and `/settings/tags` (today's tag-color table, relocated). `/settings` redirects to `/settings/home`. Verified this needs no change to `CORE_RESERVED_PATHS` or to the route/nav composition logic in `compose.ts` — its path-conflict check is a plain string comparison, indifferent to a `/*` suffix; react-router resolves the wildcard natively.

At implementation time, load the `/gravity-ui` skill to choose the correct Gravity UI primitive for the left sub-nav (not decided here).

## Risks / Trade-offs

- [Removing `CatalogConfigurationController` is a breaking backend change for any deployment relying on `CATALOG_TITLE`/`CATALOG_DESCRIPTION` env vars] → Documented as a breaking change in the proposal; `docs-site/docs/configuration/` must gain a section pointing to `atlas.config.ts` as the replacement before/alongside this ships.
- [`atlas.config.ts` cannot be overridden per-distribution without forking Core] → Accepted as a deliberate Non-Goal; flagged for a future change if/when external distributions become real (see ADR 0025).
- [A new `is_superuser`-exposing endpoint is an additional small attack surface] → Keep it minimal (boolean(s) only, no PII beyond what the session already implies), authenticated-only, and separate from allauth's own endpoints so its behavior is easy to audit in isolation.
- [`CatalogHomeSettings` as a singleton row has no established convention in this codebase to copy exactly] → Keep the model intentionally small (mirrors `Tag`'s simplicity) and document the singleton-access pattern chosen inline in code rather than inventing a generic "settings framework."

## Migration Plan

1. Backend: add `CatalogHomeSettings` model + schema migration, then a `RunPython` data migration seeding the default Markdown (mirrors `0007_reset_tag_colors.py`). Add its admin-gated read/write API. Add the `isAdmin`-exposing endpoint.
2. Backend: remove `CatalogConfigurationController`/schema/urls/settings vars/test in the same or a follow-up commit — coordinate so a deployed frontend never points at a removed endpoint (frontend and backend for this change should ship together, not independently, since the frontend `atlas.config.ts` cutover and the backend removal are two halves of one breaking change).
3. Frontend: add `atlas.config.ts`; wire `AppShell.tsx` and `HomePage.tsx` to it; remove `catalogConfigurationApi`/`CatalogConfiguration`.
4. Frontend: `plugins/c4/frontend` — add `navItems.ts` + route, remove the `homeWidget` contribution, add the zero-Systems empty state to the System Map page.
5. Frontend: rebuild `HomePage.tsx` around counts + the new `CatalogHomeSettings`-backed "About this catalog" section.
6. Frontend: `AdminProtected`, nested `/settings/*` routing (`SettingsLayout`, `/settings/home`, `/settings/tags` moved from the current flat `SettingsPage`), nav-item hiding for non-admins.
7. Docs: update `docs-site/docs/configuration/` to document `atlas.config.ts`.

No rollback beyond standard revert — no irreversible data migration (the seeded `CatalogHomeSettings` row can be left in place even if the code reverts; it's inert without the reading code).

## Open Questions

- Exact naming/shape of the `isAdmin`-exposing endpoint (`GET /api/me/` was a working name during exploration, not finalized).
- Exact singleton-access pattern for `CatalogHomeSettings` (fixed PK vs. `get_or_create` helper) — an implementation-time call, not an architectural one.
- Exact Gravity UI primitive for the Settings left sub-nav — deferred to implementation time via the `/gravity-ui` skill.
