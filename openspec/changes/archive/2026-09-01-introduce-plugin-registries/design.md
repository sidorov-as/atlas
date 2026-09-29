## Context

`backend/server/settings/components/common.py:21-39` hard-codes `INSTALLED_APPS` as a literal tuple: `server.apps.catalog`, `server.apps.ingestion`, then Django/third-party apps. There is no distinction today between "installed in the Python environment" and "selected for this deployment" — everything importable runs. `plugin-architecture.md`'s Discovery and startup section (lines 384-401) and ADR 0007 require: installing a wheel doesn't activate it, only the deployment manifest does; startup is phased so `INSTALLED_APPS` is generated *before* `django.setup()` and runtime registrations happen *after*.

This change deliberately does not yet introduce real separately-versioned plugin packages (`atlas-plugin-standard-catalog`, etc.) — that's `extract-standard-catalog-plugin` onward — or the YAML manifest/lock (`introduce-plugin-distribution-and-composer`). It proves the registry/phased-startup mechanism using the two apps that already exist in-tree, selected via a plain Python list, so later changes have a stable target to extract into instead of building the mechanism and the extraction simultaneously.

## Goals / Non-Goals

**Goals:**
- A `PluginDescriptor` with static, Django-setup-independent metadata (readable before `django.setup()`, per `plugin-architecture.md:236`).
- `INSTALLED_APPS` generated from selected descriptors' `djangoApps`, not hard-coded.
- `CapabilityRegistry`, `PermissionRegistry` exist and are populated in a runtime-entry-point phase after `django.setup()`.
- A composition-validation step runs before the process accepts traffic and fails closed on duplicate ids.

**Non-Goals:**
- Reading plugin selection from a YAML manifest — a Python-level `SELECTED_PLUGINS` setting is enough for this change.
- Actually splitting `server.apps.catalog`/`server.apps.ingestion` into separately versioned/installable wheel packages.
- Validating cross-plugin capability *dependencies* (a plugin requiring another plugin's capability) — only duplicate-id detection is implemented now; dependency-graph validation is added when a real cross-plugin capability consumer exists (`extract-c4-plugin` is the first).
- Frontend registries — this change is backend-only; `introduce-frontend-extension-points` covers the frontend side independently.

## Decisions

**Plugin descriptors are plain dataclasses/attrs objects returned by a module-level function, not Django model instances or anything requiring app registry access.** `plugin-architecture.md:236` is explicit that backend metadata "must be readable without importing Django models before `django.setup()`" — this is what makes generating `INSTALLED_APPS` from them possible at all.

**Startup phase order is enforced by a single orchestration function called from `manage.py`/WSGI entrypoint, not by relying on Django's own app-loading order.** Django's own `AppConfig.ready()` already runs after `django.setup()`, which is where the *runtime* registries (capability, permission, kind — kind registry already exists from the previous change) get populated via each app's `ready()`. The *static* phase (reading descriptors, computing `INSTALLED_APPS`) necessarily happens in `settings.py` before Django is set up at all, since `INSTALLED_APPS` is itself a setting.

**Composition validation happens once, synchronously, at process startup — not lazily on first request.** A duplicate id or missing dependency must prevent the process from ever reporting healthy, per `plugin-architecture.md`'s failure model ("composition... failures prevent the deployment from accepting traffic"). Implemented as a check run at the end of the startup orchestration function; if it raises, the process exits non-zero before binding to a port.

**`CapabilityRegistry` and `PermissionRegistry` are separate registries from `EntityKindRegistry`, not one generic "extension registry."** They have different cardinality rules (capabilities are keyed+versioned service contracts; permissions are a flat namespaced-id set; kinds are keyed like capabilities but semantically distinct) — collapsing them into one generic map would hide the `collection`/`singleton`/`keyed` cardinality distinction `plugin-architecture.md`'s extension-point model depends on later.

## Risks / Trade-offs

- [Generating `INSTALLED_APPS` dynamically makes Django startup slightly less transparent than a literal tuple in settings] → Log the resolved `INSTALLED_APPS` list at startup (already necessary for debugging a composition failure) so `manage.py diffsettings`-style introspection stays possible.
- [Two apps self-describing as "plugins" while still living in the same settings module they always have] → Keep `server.apps.catalog`'s and `server.apps.ingestion`'s descriptors literally in their own app modules (`server/apps/catalog/plugin.py`), not in `settings/`, so the later extraction changes move a self-contained file rather than untangling settings-module code.
- [A hard startup failure on composition error is a behavior change from today's "whatever's importable, imports"] → This is intentional per `plugin-architecture.md`'s failure model; document it clearly in the deployment runbook so an operator adding a second plugin later understands a duplicate id is a hard stop, not a warning.

## Migration Plan

1. Add `PluginDescriptor`, the entry-point group declaration, and the static-metadata read function. No behavior change yet — `INSTALLED_APPS` still literal.
2. Add descriptors for `server.apps.catalog` and `server.apps.ingestion`; add the `SELECTED_PLUGINS` setting listing both.
3. Replace the literal `INSTALLED_APPS` tuple with the generated list (selected descriptors' `djangoApps` + the existing third-party/Django apps, which aren't plugin-selected in this change). Verify `manage.py check` and the full test suite pass with the generated list.
4. Add `CapabilityRegistry`/`PermissionRegistry`, wire `EntityKindRegistry` population into the same "load entry points" phase, add the composition-validation step, wire a hard-fail on validation error into the startup path.
5. Rollback: revert to the literal `INSTALLED_APPS` tuple; no data/migration involved, this change is process-startup code only.

## Resolved

- **`SELECTED_PLUGINS` location**: a dedicated file (e.g. `server/settings/selected_plugins.py`), not a settings module, so `introduce-plugin-distribution-and-composer` later replaces its contents wholesale with composer-generated output rather than extracting plugin selection out of general settings.
