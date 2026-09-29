## 1. Descriptor and entry point

- [x] 1.1 Define `PluginDescriptor` (id, version, compatibility ranges, `djangoApps`, entry point reference) as a plain dataclass importable without Django models.
- [x] 1.2 Declare the `atlas.plugins` entry-point group convention (even though this change doesn't yet package plugins as separate wheels).
- [x] 1.3 Add a `SELECTED_PLUGINS` setting/file listing the plugins active for this deployment.

## 2. Static phase

- [x] 2.1 Add descriptors for `server.apps.catalog` and `server.apps.ingestion` (`server/apps/catalog/plugin.py`, `server/apps/ingestion/plugin.py`).
- [x] 2.2 Replace the literal `INSTALLED_APPS` tuple in `backend/server/settings/components/common.py` with a list generated from selected descriptors' `djangoApps` plus the existing non-plugin apps.
- [x] 2.3 Verify `manage.py check` and the full backend test suite pass against the generated `INSTALLED_APPS`.

## 3. Runtime phase

- [x] 3.1 Add `CapabilityRegistry` and `PermissionRegistry`.
- [x] 3.2 Move `EntityKindRegistry` population into a shared "load selected runtime entry points" phase alongside the two new registries.
- [x] 3.3 Add the composition-validation step (duplicate capability/permission/kind id detection).

## 4. Startup orchestration

- [x] 4.1 Wire read-descriptors → verify → generate `INSTALLED_APPS` → `django.setup()` → load entry points → assemble registries → validate → accept traffic into a single orchestration path used by `manage.py`/WSGI/ASGI entrypoints.
- [x] 4.2 Make composition validation failure exit the process non-zero before it binds its listening port.
- [x] 4.3 Add a startup log line listing the resolved `INSTALLED_APPS` and registered capability/permission/kind ids for operability.
