## 1. Scaffold the plugin packages

- [x] 1.1 Create `plugins/standard-catalog/backend/` (`atlas_plugin_standard_catalog`) with an empty `PluginDescriptor`.
- [x] 1.2 Create `plugins/standard-catalog/frontend/` (`@atlas/plugin-standard-catalog`) with an empty `defineFrontendPlugin`.
- [x] 1.3 Wire both into `SELECTED_PLUGINS` / `installedFrontendPlugins` contributing nothing yet; verify the app still builds and runs unchanged.

## 2. Move Team (Group) and Actor (User)

- [x] 2.1 Move `GroupDetails` model and formalize `GroupKindHandler`, registered from the new backend package.
- [x] 2.2 Move Team's frontend contributions (route, nav item, detail tabs: Overview/Members/Systems/Components/Resources/APIs) into the new frontend package.
- [x] 2.3 Verify `catalog-web-ui` Team scenarios and `entity-catalog`'s Group read-only-via-API scenarios.
- [x] 2.4 Move `ActorDetails` model and formalize `ActorKindHandler`, registered from the new backend package; verify `Group.members` and Architecture Relationship references to Actors still resolve.
- [x] 2.5 Add an ingestion source for Actor (following `add-api-spec-source`'s precedent) so `ActorKindHandler` accepts Entity Intents; verify actors declared through it are created/reconciled like any other ingested entity. Django admin remains the only interactive management surface — no frontend create/edit form.

## 3. Move Resource, Component, System

- [x] 3.1 Move `ResourceDetails`/`ResourceKindHandler` and Resource's contributions; verify scenarios.
- [x] 3.2 Move `ComponentDetails`/`ComponentKindHandler` and Component's contributions; verify scenarios.
- [x] 3.3 Move `SystemDetails`/`SystemKindHandler` and System's contributions; verify scenarios.

## 4. Shrink core

- [x] 4.1 Confirm `server.apps.catalog` no longer imports System/Component/Resource/Group; delete dead code.
- [x] 4.2 Confirm `frontend/src/plugins/core/` no longer contributes System/Component/Resource/Team routes/tabs/nav; delete dead code.
- [x] 4.3 Add `REQUIRED_PLUGINS = {'atlas.standard-catalog'}` to the composition validator; add a test asserting composition fails when it's absent from `SELECTED_PLUGINS`.

## 5. Verify the boundary

- [x] 5.1 Run a boundary test: compose with `atlas.standard-catalog` deselected and confirm core still starts, registering zero Entity Kinds (test-only configuration, not a supported deployment).
- [x] 5.2 Run the full backend + frontend test suite against the extracted layout.
