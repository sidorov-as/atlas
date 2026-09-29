## Why

C4 diagram generation (`catalog-c4-diagrams`, `system-architecture-diagram`, `c4-diagram-viewer-preferences` specs) currently lives inside `server.apps.catalog` and its API, and is rendered from System/Component data the same code that owns those kinds also owns. `plugin-architecture.md` picks C4 as the proof point for cross-kind capabilities, detail tabs, home widgets, backend rendering, and permissions together (§ "Proving the architecture", item 3) — it's the first plugin that must target *which entities support diagrams* semantically (`entitySupports('architecture.subject.v1')`) instead of hard-coding `kind === 'system' or kind === 'component'`, and the first to register its own permission (`atlas.c4.diagram.read`) checked by the core Authorization Service rather than an ad hoc view-level check.

## What Changes

- Create `plugins/c4/` (backend `atlas_plugin_c4` + frontend `@atlas/plugin-c4`), declaring a manifest dependency on `atlas.standard-catalog` (diagrams read System/Component/Resource/Group data) and an optional one on `atlas.apis` (API entities can appear in diagrams when present).
- Add the `EntityCapability` mechanism in full: Entity Kinds declare `provides=[...]` (e.g. `system`/`component` declare `architecture.subject.v1`; `group` and `actor` declare `architecture.actor.v1`); the frontend's `entitySupports(capability)` predicate (already stubbed as a typed helper in `introduce-frontend-extension-points`) becomes real, checked against the registry.
- Generalize C4's rendering of Architecture Relationship endpoints: an endpoint whose kind declares `architecture.subject.v1` renders as a boxed System/Component-style element; one declaring `architecture.actor.v1` renders as a C4 Person. This replaces today's hard-coded "User or Group renders as a Person" check (`architecture-relationships` spec) with the same capability-targeting mechanism used for the C4 tab itself, and is what lets `introduce-database-schema-facet`'s later capability (`schema.host.v1`) and any future kind opt into either rendering role without `atlas.c4` changing.
- Move PlantUML rendering, the diagram endpoints (`/api/diagrams/...`), viewer preferences, and the C4 Diagram/System Architecture detail tabs into the plugin. Register the `atlas.c4.diagram.read` permission and check it via the core Authorization Service (formalized fully in `introduce-auth-provider-extension`, but the permission-declaration/check pattern is usable as soon as *a* policy evaluator exists — for this change, a minimal always-allow-if-authenticated evaluator is enough, since the pre-existing behavior has no per-diagram ACL).
- Add a home widget contribution (the empty extension point added in `introduce-frontend-extension-points` gets its first real contributor) — not present in the current PoC, so this is genuinely new functionality this change introduces, matching the conversation's C4-as-plugin example ("на главную").
- **BREAKING (internal)**: `catalog-c4-diagrams`/`system-architecture-diagram`/`c4-diagram-viewer-preferences` code moves out of `server.apps.catalog`; diagram endpoint paths may move under `/api/plugins/atlas.c4/...` per `plugin-architecture.md:420` (decide exact paths in design.md) — response bodies (SVG/PNG image bytes) are unchanged.

## Capabilities

### New Capabilities
- `entity-capabilities`: an Entity Kind declares which semantic capabilities it provides; a frontend or backend contribution targets a capability (`entitySupports(...)`) instead of hard-coding a kind list, so a future kind can opt into an existing view without the owning plugin changing.
- `c4-plugin`: C4 diagram generation, viewing, and preferences are provided entirely by an optional plugin targeting `architecture.subject.v1`-capable entities, with its own registered permission and (new) home widget.

### Modified Capabilities
- `architecture-relationships`: the "Explicit User and Group interactions are represented as C4 People" requirement is generalized from naming `User`/`Group` explicitly to "any entity whose kind declares `architecture.actor.v1`" (which `group` and `actor` both declare after this change) — behaviorally identical for the two kinds that exist today, but the mechanism is now capability-driven.
- `catalog-c4-diagrams`, `system-architecture-diagram`, `c4-diagram-viewer-preferences`: no requirement text changes beyond what's already covered — every existing scenario must keep passing — this change relocates their implementation behind `entitySupports('architecture.subject.v1')` instead of a hard-coded kind check, which is a mechanism change, not a behavior change (see design.md's Migration Plan for how that's verified).

## Impact

- **Backend**: new `plugins/c4/backend/`; PlantUML rendering/diagram endpoints move; `EntityKindRegistry`/`CapabilityRegistry` gain the `provides=[...]` declaration surface (backend Entity Kinds declaring capabilities) used by Standard Catalog (`system`/`component` declare `architecture.subject.v1`; `group`/`actor` declare `architecture.actor.v1`) and, optionally, APIs.
- **Frontend**: new `plugins/c4/frontend/`; `entitySupports()` becomes a real predicate; C4/System Architecture detail tabs and the new home widget move/are added.
- **Permissions**: first plugin-declared permission (`atlas.c4.diagram.read`), first real use of the core Authorization Service beyond the existing session-based `catalog-auth` check.
- **Dependents**: `introduce-database-schema-facet` reuses the same capability-targeting pattern for a second, unrelated view (ER diagrams on `schema.host.v1`); `introduce-auth-provider-extension` replaces this change's minimal always-allow evaluator with a real pluggable one.
