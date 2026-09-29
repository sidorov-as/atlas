## Context

After changes 1-4, `server.apps.catalog` contains System/Component/Resource/Group (`*Details` + `*KindHandler`) plus the Entity Service, registries, and generic API infrastructure all mixed together, and `frontend/src/plugins/core/index.ts` contains every route/tab contribution for the same four kinds. This change is the first exercise of `plugin-architecture.md`'s core boundary claim (lines 67-98): "Atlas Core contains no concrete Entity Kinds." It's also the first change that gives the future monorepo layout (`plugins/standard-catalog/`, per ADR 0024) a real home, ahead of `introduce-plugin-distribution-and-composer` formalizing the whole `atlas/` tree.

## Goals / Non-Goals

**Goals:**
- `server.apps.catalog` and the frontend "core" module contain zero System/Component/Resource/Team-specific code after this change.
- Standard Catalog is built and selected as an independently identifiable plugin (own `PluginDescriptor`, own frontend package boundary) even though it still lives in the monorepo and isn't yet published to a registry.
- Every `entity-catalog`, `entity-identity`, `entity-relations`, `catalog-auth`, `catalog-web-ui` scenario involving System/Component/Resource/Team passes unmodified.

**Non-Goals:**
- Publishing `atlas-plugin-standard-catalog`/`@atlas/plugin-standard-catalog` to a real PyPI/npm registry — workspace/path dependencies are enough until `introduce-plugin-distribution-and-composer`.
- Building the real deployment manifest's "required plugin" enforcement — this change hard-codes the requirement as a composition-validator check that fails if `atlas.standard-catalog` is absent from `SELECTED_PLUGINS`, to be replaced later.
- Touching API, C4, or ingestion — those stay wherever they currently are; this change only proves the pattern on the four Standard Catalog kinds.

## Decisions

**Actor moves with Team, not separately.** Both are admin-managed kinds with no frontend create/edit form — Actor even more so, since it has no frontend pages at all today. Treating it as a fifth Standard Catalog kind rather than leaving it in a shrinking core (or inventing a separate tiny plugin for one thin model) keeps the "core has no concrete kinds" boundary exact and avoids a bespoke exception for the one kind this program didn't originally plan for.

**Actor becomes ingestible; Team does not.** `ActorKindHandler` accepts Entity Intents from an ingestion source (e.g. a static file source, following `add-api-spec-source`'s precedent), so operators can declare actors in a manifest-like way instead of only through Django admin. This is scoped to Actor specifically — it's needed now for `extract-c4-plugin`'s `architecture.actor.v1` capability and is the kind operators will most plausibly want to declare in bulk, and Actor's admin-managed-only status was never an architectural requirement, just the status quo (unlike Team, which stays non-ingestible: no concrete need identified). Django admin remains the only *interactive* management surface for Actor; no frontend create/edit form is built for it in this change.

**Login and Settings pages stay core-owned, not part of Standard Catalog.** Login is Authentication Core's concern (formalized in `introduce-auth-provider-extension`); Settings currently shows tag management, which is closer to a core cross-cutting concern than a Standard-Catalog-specific one. Treating them as core-owned now avoids re-homing them twice.

**`Relation`, `EntityService`, both registries, and generic API infrastructure (pagination, filtering shared helpers) stay in `server.apps.catalog` (or are renamed to a genuinely neutral `server.apps.entities`/`server.apps.core` at this point, since the app no longer holds any kind).** Renaming the Django app label is a bigger migration-history risk than leaving the label as `catalog` while its contents become kind-agnostic — default to keeping the label, revisit the rename only if the empty-of-kinds `catalog` app label reads as actively confusing once APIs/C4/Ingestion are also extracted.

**"Required plugin" is enforced by the composition validator added in `introduce-plugin-registries`, extended with a hard-coded `REQUIRED_PLUGINS = {'atlas.standard-catalog'}` check.** This is explicitly a stand-in — `introduce-plugin-distribution-and-composer` replaces it with a manifest-driven required-plugin list — but building it now means this change's own tests can assert the requirement is enforced, rather than leaving it undeclared until much later.

## Risks / Trade-offs

- [Moving four kinds' worth of models/migrations to a new Django app changes migration history/app labels, which Django treats carefully] → Use `django.db.migrations` app-label-preserving move patterns (keep the same `app_label` in `Meta` while the Python package moves, or run a documented `makemigrations --merge`-free relabel); verify with a fresh-database migrate and an existing-database migrate-from-previous-state both succeeding.
- [Frontend package split could accidentally introduce a circular workspace dependency between `plugin-standard-catalog` and whatever remains "core"] → Add the CI import-boundary check from `introduce-plugin-distribution-and-composer` early, scoped just to this pair, rather than waiting for that change to land.
- [Nothing yet validates that Standard Catalog *cannot* reach into core internals, since there's only one other plugin to violate the boundary against] → This is inherent to being the first extraction; `extract-apis-plugin`'s manifest-dependency-on-Standard-Catalog is the first case that exercises cross-plugin (not core-plugin) boundary enforcement.

## Migration Plan

1. Scaffold `plugins/standard-catalog/backend/` and `plugins/standard-catalog/frontend/` as workspace packages with their own `PluginDescriptor`/`defineFrontendPlugin` shells, contributing nothing yet.
2. Move `GroupDetails`+`GroupKindHandler` and `ActorDetails`+`ActorKindHandler` (formalizing Team and Actor as registered kinds) first, since both are currently the simplest, least cross-referenced models; verify Teams pages, `catalog-web-ui` Team scenarios, and that Actor references from `Group.members` and Architecture Relationships still resolve.
3. Move Resource (`ResourceDetails`+`ResourceKindHandler` + frontend contributions), then Component, then System, each verified against their `catalog-web-ui`/`entity-catalog` scenarios before moving the next.
4. Delete the moved code from `server.apps.catalog`/`frontend/src/plugins/core/`; confirm nothing there still imports System/Component/Resource/Group.
5. Add `REQUIRED_PLUGINS` enforcement; verify composition fails if `atlas.standard-catalog` is removed from `SELECTED_PLUGINS`.
6. Rollback: each kind's move (step 2-3) is independently revertible; step 4's deletion should only happen after all four kinds are confirmed moved and tested.

## Open Questions

- Should the Django app label become `server.apps.catalog` → `server.apps.core` once it's kind-agnostic, now or later? Leaving as a follow-up decision once `extract-apis-plugin`/`extract-c4-plugin`/`extract-ingestion-plugin` have also landed and it's clear what, if anything, is left in `apps.catalog`.
