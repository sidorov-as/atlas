## Why

`introduce-entity-kind-registry-and-service` added one registry (Entity Kinds) populated by in-tree `AppConfig.ready()` calls. `plugin-architecture.md` needs several more registries — capability, permission, and plugin identity itself — and, critically, needs them populated from a deployment-selected set of installed apps rather than everything importable in the environment (ADR 0007: discover *selected* backend wheels by entry point, not by scanning). It also needs the phased startup sequence (`plugin-architecture.md:388-399`) that fails composition before traffic is accepted, rather than letting a broken plugin degrade silently. Nothing in the current codebase resembles this: `INSTALLED_APPS` in `backend/server/settings/components/common.py` is a hard-coded tuple, and there is no concept of "selected" versus "importable."

## What Changes

- Add a `PluginDescriptor` shape (`id`, `version`, compatibility ranges, `entryPoint`) and a Python `atlas.plugins` entry-point group that a distribution (a Django project, for now still this monorepo's own `backend/server`) declares.
- Add a `SelectedPlugins` resolver that reads an explicit list (initially a Python list/setting, not yet the YAML manifest from `introduce-plugin-distribution-and-composer`) and computes `INSTALLED_APPS` from only the selected plugins' declared `djangoApps`, generated *before* `django.setup()`.
- Add `CapabilityRegistry` and `PermissionRegistry` alongside the existing `EntityKindRegistry`, all populated during a new "load selected runtime entry points" startup phase that runs *after* `django.setup()`.
- Add a composition-validation step that runs after all registries are populated and before the app accepts traffic: duplicate id detection (kind/capability/permission), and (stub for now, filled in by later changes) missing required capability/dependency detection.
- Wire Django's startup (or a dedicated `AppConfig.ready()` on a new `server.apps.plugins` app) to run: read selected descriptors → verify identities → generate `INSTALLED_APPS` → `django.setup()` → load entry points → assemble registries → validate composition → accept traffic, matching `plugin-architecture.md:390-399`.
- This change keeps `server.apps.catalog` and `server.apps.ingestion` as the only two selectable "plugins" (self-describing, not yet split into separate packages) — proving the mechanism without yet doing the plugin *extraction* work of later changes.

## Capabilities

### New Capabilities
- `plugin-registries`: capability, permission, and plugin-identity registries exist alongside the Entity Kind registry, are populated only from operator-selected plugins during a phased startup, and composition failures (duplicate ids, unresolved required dependencies) prevent the process from accepting traffic.

## Impact

- **Backend**: new `server.apps.plugins` (or equivalent) app owning descriptor loading and registry assembly; `backend/server/settings/components/common.py`'s hard-coded `INSTALLED_APPS` is replaced by a generated list; `server.apps.catalog` and `server.apps.ingestion` each gain a `PluginDescriptor`.
- **Startup behavior**: a composition failure (e.g. a duplicate registered id) now prevents the backend process from starting, where today a duplicate would either silently overwrite an in-memory registration or never be checked.
- **Dependents**: `extract-standard-catalog-plugin`, `extract-apis-plugin`, `extract-c4-plugin`, `extract-ingestion-plugin`, `introduce-auth-provider-extension` all register through these registries instead of ad hoc `AppConfig.ready()` calls; `introduce-plugin-distribution-and-composer` replaces the "explicit list" selection mechanism with the real manifest/lock.
