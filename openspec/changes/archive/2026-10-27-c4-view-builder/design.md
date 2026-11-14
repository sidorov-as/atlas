## Context

`atlas.c4` renders diagrams on the server: builders in `c4.py` turn catalog data into a PlantUML payload, a local PlantUML backend renders it, and the frontend shows the result as an `<img>` inside a pan/zoom viewer. The existing builders (System Landscape, System Context, System Architecture, Component) each have a fixed scope and accept only rendering options (layout, title, legend, labels, sprites, stereotypes), which the viewer persists per view in local storage.

All builders draw from the same sources and rules, which the new builder must reuse:

- declared `ArchitectureRelationship` rows, with their label, technology, and interaction kind;
- derived `Relation` rows limited to `consumesAPI`, `providesAPI`, and `dependsOn`, labelled "Uses";
- a declared edge supersedes a derived edge with the same directed visible endpoints (`_merge_edges`);
- at system level, entities collapse to their owning System (`_context_endpoint`); actor kinds (any kind declaring `architecture.actor.v1`, currently `group` and `actor`) stay themselves and appear only through declared relationships;
- ownership never creates actors.

Entity facts that shape the design: Component and API always belong to a System; Resource may have no System. Diagram access is gated only by `atlas.c4.diagram.read`. The optional search plugin is not guaranteed to be installed, but standard-catalog list endpoints support name search, a `system` filter, and pagination.

Until now `atlas.c4` has been stateless: it has no models and no migrations. Saved views make it the first owner of data in this plugin, in the same spirit as `atlas.flows`, whose `Flow` is a hand-authored object that references catalog entities without being a catalog entity itself.

## Goals / Non-Goals

**Goals:**
- Let a user narrow a C4 diagram to a chosen slice of the catalog, in two clearly defined modes, at system or component level.
- Let users save, name, edit, and delete such slices as views, listed with pagination and opened as a diagram, in the way flows are.
- Reuse the existing model, relationship rules, PlantUML pipeline, styling, and viewer.
- Fail loudly and early (limit, unknown entities) instead of silently dropping nodes.

**Non-Goals:**
- Ownership, private views, or version history of views.
- Manual layout, interactive graph, catalog editing from the diagram.
- Filters by owner, tags, or lifecycle.
- Per-entity access control on diagram content.
- Any change to existing diagram endpoints or Landscape output.

## Decisions

### 1. A new builder and endpoint, not parameters on existing ones

Add `build_custom_view` and endpoints beside the existing diagram endpoints (decision 5). Shared helpers (`element`, `relationship`, `_merge_edges`, `diagram_payload`, element mapping) are reused.

Alternatives considered:
- *Extend the Landscape and Architecture builders with filter parameters.* Rejected: Landscape would stop meaning "everything", and Architecture is defined around one System with its direct neighbors; both would accumulate branching and their specs would blur.
- *Compose the result from existing builders and post-filter the payload.* Rejected: those builders pre-apply scope rules (for example, external-only-if-directly-connected) that would prevent the requested semantics, such as multi-system selections or depth greater than one.

### 2. Build the level graph in memory, then select

For the chosen level, load nodes and edges once (as the existing builders already do: all declared relationships and the three derived predicates), apply the relationship-source filter, then run selection:

- *Selected only*: nodes = selection; edges = edges with both ends in the selection.
- *Neighborhood*: breadth-first traversal from the roots on the level graph, honoring depth, direction, and entity-type filters.

At system level, edge endpoints are first collapsed to Systems (and actors), and traversal runs on the collapsed graph, so depth means "systems away". At component level, nodes are Components, Resources, and APIs (plus actors); an edge is kept when both ends are nodes of those kinds.

Alternatives considered:
- *Recursive SQL / graph query per hop.* Rejected: the relationship tables are small relative to catalog size, the existing builders already load them whole, and an in-memory traversal keeps one code path for both levels and both sources.
- *Compute depth on the raw entity graph, then collapse.* Rejected: depth would not match what the user sees at system level.

### 3. Actors are optional leaves

An "Actors" entity type controls whether actor-capable kinds are shown. In Neighborhood mode an actor adjacent to a visited node is added but never expanded further unless it is a selected root. In Selected-only mode actors are ordinary members of the selection. Kinds are discovered via the `architecture.actor.v1` capability, not a hard-coded list.

Alternatives considered:
- *Exclude actors entirely.* Rejected: the Architecture tab (the builder's entry point) shows them, so the builder would appear to lose data; "who uses this system" is a common question.
- *Treat actors as normal traversal nodes.* Rejected: one person linked to many systems pulls them all in at depth two ("hub effect").
- *Show only the `actor` kind, not `group`.* Rejected: would hard-code kinds that the capability model is designed to avoid; authors already opt in per relationship.

### 4. Node limit checked before PlantUML

A plugin configuration value (`maxNodes`) bounds the number of visible nodes. Boundary frames and decorative elements do not count. The check runs after selection and before payload rendering, and it also applies to Unlimited depth. The response is a structured error naming the limit and the resulting count. The limit is a plugin configuration setting (`maxNodes`) with a default of 50; operators can raise or lower it. The default is validated for readability against the demo catalog during implementation and changed only if 50 proves unreadable. Because selected entities are always visible, the same limit also bounds the number of entities in a view's settings, so no separate cap on selection size is needed.

Alternatives considered:
- *Truncate silently to the limit.* Rejected: misleading diagrams.
- *Limit by relationship count.* Rejected for now: node count is easier to explain in an error message and bounds edges in practice; the error may report both numbers.
- *Rely on the PlantUML timeout.* Rejected: slow and gives no actionable guidance.

### 5. Transport: POST for the draft preview, GET by id for saved views

Two endpoints share one builder:

- `POST /api/plugins/atlas.c4/diagrams/custom/` takes the settings as a JSON body and returns the SVG. The editor uses it to preview a draft that has not been saved. Rendering options (layout, legend, and the others) travel as query parameters, as for other diagrams, because they are viewer preferences and not part of a view.
- `GET /api/plugins/atlas.c4/views/{id}/diagram/` renders a saved view, with `format=svg|png` and the existing `download` and rendering parameters. It is a plain link, so `<img>`, PNG, and download work like other diagrams.

Entity references are UUIDs (the identifier the diagram endpoints already use). The old `GET diagrams/custom/` with repeated `entity` parameters is removed so there is one representation of the contract.

Both the editor preview and the detail page request the SVG with `fetch` and an `AbortController`, show it through an object URL, and read failures from HTTP status and a JSON error body (400 invalid parameters, 404 unknown entity, 422 limit exceeded). This gives actionable errors and cancels superseded requests. Existing detail-page viewers keep their current `<img>` behavior; the viewer component is generalized only to accept a source and an error callback. A draft has no PNG or download link; those are offered once the view is saved.

Alternatives considered:
- *Keep GET with query parameters for the preview.* Rejected: two contracts for one builder, long URLs, and the requirement is to keep settings out of links.
- *`<img src>` as today.* Rejected: errors become an opaque broken image, and stale responses need extra bookkeeping.
- *A JSON response carrying SVG plus metadata (counts, warnings).* Rejected: counts are not required, and it would complicate PNG and download links.
- *Render only saved views (save before preview).* Rejected: users would have to create junk views to see what a setting does.

### 6. Boundaries at component level

Component-level output draws a boundary per System, containing only the selected or discovered elements, and never adds the rest of that System's components. Resources without a System are drawn outside any boundary. Boundary frames are styling only.

### 7. Layout and display options reuse viewer preferences

The builder has no Layout control. Layout, title, legend, and other display options come from the existing viewer gear, stored under a view key for custom views. They are not part of a saved view; every viewer sees a view with their own preferences, as with other diagrams. This replaces a draft idea of a Layout dropdown in the panel, which would have duplicated the gear.

### 8. Draft and applied state live in the editor

The editor form holds a draft and an applied copy. **Apply view** sends the draft to the preview endpoint and, on success, makes it the applied copy; field changes alone never trigger rendering. **Save** persists the draft (name, description, settings) and returns to the view detail. Heading, legend, and the preview always refer to the applied copy. Leaving the editor with unsaved changes asks for confirmation. Nothing about the applied state is stored in the URL, so there is no Back/Forward restoration of applied settings.

### 9. Entity picker uses per-kind list endpoints

The picker queries the relevant list endpoints with name search and a small page size, merges results client-side, and shows the kind and System for each result. This works without the optional search plugin. Actor-capable kinds are included only when the Actors type is enabled.

Alternatives considered:
- *Use the search plugin.* Rejected: optional, and results lack System information.
- *Add a dedicated picker endpoint in `atlas.c4`.* Deferred: more surface area than the existing endpoints need; revisit if merging per-kind pages proves awkward.

### 10. Actor kinds come from a small endpoint in the C4 plugin API

The picker needs to know which kinds are actors in order to search them when the Actors type is enabled. The `atlas.c4` API gains a small read-only endpoint (`GET /api/plugins/atlas.c4/custom-view/actor-kinds/`) returning the actor-capable kinds (kind id and label), resolved through the `architecture.actor.v1` capability and gated by `atlas.c4.diagram.read`. The builder uses the same resolution for validating selections, so the picker and the diagram endpoint agree on what an actor is.

Alternatives considered:
- *Hard-code `actor` and `group` in the frontend.* Rejected: a new kind declaring the capability would be selectable in the diagram endpoint but invisible in the picker.
- *Infer actor kinds from existing frontend plugin capability data.* Rejected: it ties the picker to frontend registry details that the C4 plugin does not own and makes the contract with the backend implicit.

### 11. The `View` model

`View` lives in `atlas_plugin_c4` with: `id` (UUID primary key), `name` (up to 255 characters), `description` (text, may be empty), `settings` (JSON), `created_at`, and `updated_at`. Name uniqueness ignores case, enforced by a database `UniqueConstraint` on `Lower("name")`, and a violation is reported as a validation error on the name field. `settings` holds level, selection mode, entity UUIDs, depth, direction, entity types, and relationship source; it is validated by the same schema that validates the preview request, so a stored view always has a well-formed shape. Entities are referenced by UUID inside the JSON, not by foreign key or many-to-many, matching how `Flow.steps` references entities. Listing is paginated, searchable by name, and sortable by name (ascending by default, descending on request), as the Flows list is; no other ordering is offered.

Alternatives considered:
- *Many-to-many table to entities.* Rejected: it would block entity deletion or need cascade rules for something that is purely a stored selection, and the node limit already bounds the list.
- *Separate columns for level and mode.* Rejected: nothing filters on them, and the JSON keeps the schema in one place.
- *Case-sensitive uniqueness.* Rejected: "Billing" and "billing" would be indistinguishable in a list.

### 12. Permissions

Views are shared across the catalog. Reading and rendering use `atlas.c4.diagram.read`. Writes use new permissions registered by the plugin. `RBACPolicyEvaluator` resolves a permission by its suffix, and with no resource: `.create` and `.delete` allow any authenticated principal, `.edit` allows only a superuser (it checks group membership of a missing owner), and an unrecognised suffix such as `.update` is denied. The core guard additionally denies write permissions to read-only principals. The plugin therefore registers `atlas.c4.view.create` and `atlas.c4.view.delete`, and checks `atlas.c4.view.create` for edits as well, so any authenticated non-read-only user can create, edit, and delete views. The permission names and this suffix behavior are documented next to the registration so they are not "fixed" later into something that locks out users.

Alternatives considered:
- *Ownership by creator (`created_by`).* Deferred: shared views fit the catalog model; private views are listed as out of scope.
- *Superuser-only edit via `atlas.c4.view.edit`.* Rejected: it would make views effectively read-only for normal users.

### 13. Views can reference entities that no longer exist

Because settings hold entity UUIDs, a view can outlive an entity. Reading a view returns it with the ids that no longer resolve. Rendering such a view fails with the existing 404 `unknown_entity` error naming the entity, rather than drawing a partial diagram. The detail page and the editor show a warning that names the missing entities; the editor offers removal from the selection, and saving after removal repairs the view. This is the same snapshot-with-warning treatment `atlas.flows` gives dangling step references.

### 14. Routes and screens

- Views list: `/system-map?tab=views`, with a `page` parameter for pagination, alongside the existing Landscape tab. It follows `FlowsListPage`: a search bar (`FilterBar`) above an `EntityActionsTable` with Name and Description columns, name sorting, and Edit and Delete row actions (Delete confirms), plus a Create view button, all hidden for read-only users.
- Create: `/system-map/views/new`. Detail: `/system-map/views/:id`. Edit: `/system-map/views/:id/edit`. Create and Edit are write routes, as in flows.
- "Open in view builder" on the Architecture tabs links to `/system-map/views/new?root=<uuid>`. The editor resolves the entity, derives the level from its kind, and applies defaults: Neighborhood mode, depth 1, direction Both, declared only, all entity types. This is a one-shot prefill, not stored view state.
- The editor shows the preview on the left and the View settings panel on the right. The panel is collapsible, open by default, and uses the same toggle control as the flow editor. Name and description are fields at the top of the panel. On narrow screens the panel sits above the preview.
- The detail page shows the diagram in the viewer with Edit and Delete actions; Delete asks for confirmation and returns to the list.

## Risks / Trade-offs

- [Neighborhood at large depth still hits the limit quickly on well-connected hubs] → The limit error suggests reducing depth or selection; actors as leaves already removes the worst hub.
- [Derived edges depend on the three existing predicates, so some real dependencies are absent in "Declared + derived"] → Same behavior as other diagrams; documented in the feature page.
- [Resources without a System appear outside any boundary at component level and vanish at system level] → Consistent with existing system-level collapse; noted in the spec.
- [A saved view stores rules and entity ids, so it can change as the catalog changes or point at a removed entity] → Removed entities produce a named warning and a refusal to render (decision 13); other changes are the intended behavior of a live view and are stated in the docs.
- [Any authenticated user can edit or delete any view] → Deliberate for shared views; private views and ownership are out of scope.
- [Permission names depend on suffix-based evaluator behavior] → Documented at the registration; covered by tests that a normal user can create, edit, and delete and a read-only user cannot.
- [First migration in a plugin that had none] → Verify plugin composition picks up migrations for the `c4_plugin` app label and that the migration-lint workflow accepts it.
- [Generalizing the viewer touches shared code] → Keep the generalization additive (new props); existing viewers and their tests must remain unchanged.
- [Default node limit may be too low or too high] → Configurable; tune against real data before release.

## Migration Plan

One new table (`View`) added by a migration in `atlas_plugin_c4`, plus a new configuration key with a default and new frontend code. No existing data changes. Rollback is migrating the plugin back (dropping the table) and removing the Views tab; existing diagrams are unaffected. Documentation for the C4 feature page ships with the change.

## Open Questions

- ~~Whether the default `maxNodes` of 50 gives readable diagrams.~~ Checked against the booking demo catalog (8 Systems, 47 Components/Resources/APIs), rendered with the local PlantUML. Systems-level views (4 to 8 nodes) and Neighborhood views up to 26 nodes read clearly. A selection of 47 nodes with declared plus derived relationships (61 edges) renders at about 4000 px wide; it is dense where many services share one API but stays legible in the pan and zoom viewer, so the default stays at 50. No larger catalog was available to test; operators with dense catalogs can lower `maxNodes`.
