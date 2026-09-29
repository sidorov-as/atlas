## Context

C4 generation is scattered across `server.apps.catalog`: diagram endpoints, PlantUML model-building from System/Component/Resource/Architecture-Relationship data, and viewer-preference storage. The frontend's `DiagramTab.tsx` and System/Component detail pages hard-code which kinds get a C4 tab. `plugin-architecture.md`'s Entity capabilities section (lines 186-205) is explicit that this is exactly the wrong shape: "cross-plugin contributions should default to targeting entity capabilities/facets... rather than a list of known kind IDs" (ADR 0023), so a future kind (e.g. a `DataProduct` from `docs/conversation.txt`'s later exchange) could opt into C4 diagrams without `atlas.c4` changing.

This is also the first change with a real permission (`atlas.c4.diagram.read`) and the first backend-rendering plugin (PlantUML), so it's where `plugin-architecture.md`'s permission-declaration pattern (ADR 0016) gets exercised for the first time, ahead of `introduce-auth-provider-extension` building the full pluggable policy-evaluator story.

## Goals / Non-Goals

**Goals:**
- Entity Kinds declare `provides=[...]` capabilities; `entitySupports(capability)` on the frontend and an equivalent backend check both resolve against the registry, not a kind list.
- System and Component (currently the only two kinds with C4 tabs) declare `architecture.subject.v1`; the C4 plugin's tab/endpoint targeting uses only that capability.
- `atlas.c4.diagram.read` is a registered permission, checked by *a* policy evaluator (minimal for now) rather than an inline view check.
- A home widget contribution exists and renders something (the System Landscape, the one existing catalog-wide diagram, is the natural first widget).
- Every `catalog-c4-diagrams`/`system-architecture-diagram`/`c4-diagram-viewer-preferences` scenario passes unchanged.

**Non-Goals:**
- Building the full pluggable Authorization Service / multiple policy evaluators (RBAC vs OPA) — `introduce-auth-provider-extension` does that. This change needs only enough of a `PermissionRegistry` + "does the current session have this permission" check to register and gate one real permission; the evaluator behind it can be a minimal always-true-if-authenticated stand-in matching current behavior exactly (no diagram ACL exists today).
- Resource or API declaring `architecture.subject.v1` — Resources appear *inside* diagrams (as `ComponentDb`/`ComponentQueue` elements per `catalog-c4-diagrams`) but aren't themselves diagram subjects with their own C4 tab today; keep that distinction, don't expand scope.
- Moving Architecture Relationships (`architecture-relationships` spec) into the C4 plugin — relationships are catalog-wide data Standard Catalog's ingestion/manual-edit paths write to (via the Relations tab), consumed by C4 but not owned by it; they stay wherever `introduce-catalog-entity-identity`'s relation model lands (core/Standard Catalog boundary — treat as core-adjacent shared data, not C4-owned).

## Decisions

**`architecture.actor.v1` is a distinct capability from `architecture.subject.v1`, declared by `group` and `actor`, not a variant of the same capability.** They gate genuinely different rendering roles (boxed subject vs. C4 Person), so collapsing them into one capability with a role flag would just move the special-casing from "which kind is this" to "what does this capability's flag say" — no real simplification. `architecture-relationships`' existing "User or Group renders as Person, ownership alone does not" requirement generalizes directly: the diagram builder checks `entitySupports('architecture.actor.v1')` on an explicit relationship endpoint instead of checking `kind in ('user', 'group')`, with no change to the ownership-inference exclusion itself.

**`provides: list[str]` is added to `EntityKindHandler`'s registration (or a sibling `EntityKindMetadata` alongside it), read by both the backend `CapabilityRegistry` and serialized to the frontend so `entitySupports()` can check it client-side without a round trip per check.** Matches `plugin-architecture.md:190-195`'s exact shape. Alternative considered: capabilities declared only frontend-side (since only frontend `entitySupports()` exists yet) — rejected because the backend also needs to know which kinds are diagram-eligible (to validate a diagram request's target kind) without importing Standard Catalog's kind list.

**Diagram endpoints move to `/api/plugins/atlas.c4/...`** (new: `/api/plugins/atlas.c4/diagrams/system/{id}/`, etc.), per `plugin-architecture.md:417-422`'s illustrative specialized-namespace convention, rather than staying at the current `/api/diagrams/...`. This is the first specialized (non-generic-entity-CRUD) plugin endpoint namespace in the codebase — establishing the convention here means `extract-ingestion-plugin` and `introduce-database-schema-facet` follow the same pattern rather than each inventing their own. The frontend's diagram-fetching code is updated in the same change; no client outside Atlas itself depends on the old path (`catalog-c4-diagrams` doesn't specify a literal path, only response format/behavior, so this is not a spec-level break).

**`atlas.c4.diagram.read` gates the diagram endpoints and the C4/System-Architecture tabs' visibility, evaluated by a minimal `AlwaysAllowIfAuthenticated` evaluator registered as the default `PolicyEvaluator` singleton.** This preserves today's exact behavior (any logged-in user can view any diagram, per the absence of any diagram ACL in the current specs) while proving the permission-declaration and check *call sites* work end-to-end; swapping the evaluator later (`introduce-auth-provider-extension`) changes only what backs the decision, not any call site added here.

**The home widget shows the System Landscape (catalog-wide diagram) as a static/refresh-on-visit image**, reusing the existing System Landscape endpoint (`catalog-c4-diagrams`'s "Catalog-wide System Landscape" requirement) rather than inventing new backend logic — this is genuinely new *placement*, not new *data*.

## Risks / Trade-offs

- [Moving diagram endpoint paths is the first user-facing (well, frontend-consumed) URL change in this program] → No spec requirement names the literal path (`catalog-c4-diagrams` describes behavior/format, not the route), so this doesn't violate any existing spec; still, grep the frontend for every literal `/api/diagrams/` reference and update atomically in one deploy, not gradually, to avoid a mixed-version window.
- [Capability declarations are new surface area with no prior art in this codebase to validate the design against] → Keep `provides` a flat list of opaque versioned strings (as `plugin-architecture.md` illustrates) rather than inventing a richer capability-metadata shape now; a second consumer (`introduce-database-schema-facet`'s `schema.host.v1`) is the next change, which will surface whether the flat-string shape is sufficient before any third-party expectation is set.
- [PlantUML rendering (a native binary dependency, per `catalog-c4-diagrams`' "PlantUML rendering stays local" requirement) moving into a plugin package complicates the backend Docker image, which currently bundles it once for `server.apps.catalog`] → The plugin's backend package declares the PlantUML binary/C4-PlantUML includes as its own packaged dependency; document that a distribution without `atlas.c4` doesn't need to bundle PlantUML at all, which is a genuine deployment-size win from optionality, not just a rearrangement.

## Migration Plan

1. Add `provides=[...]` to `EntityKindHandler` registration for `system`/`component` (declaring `architecture.subject.v1`) and `group`/`actor` (declaring `architecture.actor.v1`); serialize capabilities to the frontend bootstrap payload.
2. Implement `entitySupports()` for real against the served capability list; keep existing hard-coded C4-tab and Person-rendering kind checks in place temporarily, running both checks in parallel in a non-blocking assertion to confirm they agree before switching.
3. Scaffold `plugins/c4/backend/` and `plugins/c4/frontend/`; move PlantUML rendering, diagram endpoints (under the new `/api/plugins/atlas.c4/...` paths), and viewer-preference storage; move the C4/System-Architecture detail tab contributions, now gated by `entitySupports('architecture.subject.v1')` instead of a kind check.
4. Register `atlas.c4.diagram.read`; add the minimal `AlwaysAllowIfAuthenticated` evaluator and wire the permission check into the diagram endpoints and tab visibility.
5. Add the home widget contribution rendering the System Landscape.
6. Verify every `catalog-c4-diagrams`/`system-architecture-diagram`/`c4-diagram-viewer-preferences` scenario against the moved code; verify a distribution without `atlas.c4` composes successfully and shows no C4 tab/widget.
7. Rollback: steps 1-2 are additive and parallel-run, safe to revert; steps 3-5 move code behind the same URLs/behavior contract and can be reverted by restoring the old in-core endpoints if a defect is found post-deploy.

## Open Questions

- Should `provides` capabilities be versioned per-kind-release or per-plugin-release (i.e. does bumping `atlas.c4`'s version ever require bumping Standard Catalog's declared `architecture.subject.v1` version too)? `plugin-architecture.md` shows `architecture.subject.v1` as a stable string; treat the `.v1` suffix as the extent of versioning for now and revisit only if a breaking capability-contract change is ever needed.
