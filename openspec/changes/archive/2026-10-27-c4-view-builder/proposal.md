## Why

On a large catalog the System Landscape and System Architecture diagrams show every relationship, so they become unreadable. Users usually want a narrower question answered: "what does this API depend on", "how are these five services connected", "what sits around this database". Today the only controls are cosmetic (layout, legend, labels); the diagram content cannot be narrowed. Atlas already holds the model (entities, declared and derived relationships) and the C4/PlantUML renderer, so a user-defined view over that model is the missing piece.

A useful slice is worth keeping: users need to save a view, name it, come back to it, adjust it, and delete it, the way they do with flows. A link that carries every setting in the query string is long, fragile, and not something a person can name or find again.

## What Changes

- System Map gets two tabs: **Landscape** and **Views**. Views is a paginated list of saved views in the style of the flows list: a search bar, a table with Name and Description columns sortable by name, Edit and Delete actions in each row, and a Create view action.
- A **View** is a saved object: `id` (uuid), `name` (required, unique ignoring case), optional `description`, and `settings` (JSON holding level, selection mode, entities, depth, direction, entity types, and relationship source). The `atlas.c4` plugin gains a model and a migration.
- Pages: a view editor (`/system-map/views/new` and `/system-map/views/:id/edit`) and a view detail (`/system-map/views/:id`) that shows the diagram with **Edit** and **Delete** actions.
- The editor shows the diagram preview with the **View settings panel on the right, collapsible and open by default**, using the same toggle as the flow editor. Name and description are edited with the settings. Settings are edited as a draft and rendered explicitly with **Apply view**; **Save** stores the view.
- Settings are not carried in URLs. The preview is built with a POST request whose body holds the settings; a saved view's diagram is served by id. The Copy link button, the URL serialization of settings, and Back/Forward restoration of applied settings are removed.
- The builder constructs a C4 diagram from a slice of the catalog, in one of two selection modes:
  - **Selected entities only**: the user picks the full node set; only relationships whose both ends are selected are drawn.
  - **Neighborhood**: the user picks root entities; the diagram adds neighbors up to a depth, in a chosen direction (both, outgoing, incoming).
- Two levels: **Systems** (system-level diagram) and **Components** (Components, Resources, and APIs, possibly from different Systems). Selections cannot mix levels.
- Entity-type filters at both levels (Components, Resources, APIs at the component level; Actors at both) and a relationship-source filter (declared only, or declared plus derived).
- Actors (kinds with the actor capability) are optional and appear only through declared relationships. In Neighborhood mode they are leaves: shown when adjacent to a visited node, never traversed through unless selected as a root. Actors can be selected as roots or as members of a selection.
- Views are shared across the catalog. Any user with `atlas.c4.diagram.read` can read them; any authenticated, non-read-only user can create, edit, and delete them.
- A saved view stores entity ids, not a snapshot. When a referenced entity is later removed, the view detail and editor warn about it instead of silently dropping it.
- Add an **Open in view builder** action to the System and Component Architecture tabs. It opens the new-view editor with that entity preselected as a Neighborhood root, using a single `root` query parameter.
- Add a server-side limit on the number of nodes (plugin setting, default 50), checked before PlantUML runs; exceeding it returns an actionable error instead of a truncated diagram.
- Add a small read-only endpoint to the C4 plugin API that lists actor kinds, so the entity picker can search actors.
- Layout, title, legend, and the other rendering options keep using the existing diagram viewer preferences; the builder adds no second layout control.

Out of scope: global search and MCP exposure of views (the list has its own name search only), view ownership or private views, version history, manual node positioning, an interactive graph with click-to-recenter, editing the catalog from the diagram, filters by owner/tags/lifecycle, per-entity access checks on diagram content (diagram access stays gated by the existing diagram read permission), and entity count/relationship count summaries.

## Capabilities

### New Capabilities
- `c4-custom-view-diagram`: Generating a C4 diagram from a user-defined selection: levels, selection modes, depth and direction traversal, entity-type and relationship-source filters, actor handling, boundaries, node limit, SVG/PNG delivery, structured errors, and the saved-view API (create, list with pagination, read, update, delete, unique name, permissions, rendering by id and by POST preview).
- `c4-view-builder-ui`: The System Map Views experience: list, detail with Edit and Delete, the editor with a collapsible right-hand settings panel, draft versus applied state, entity picker, the entry point from Architecture tabs, and loading, empty, missing-entity, and error states.

### Modified Capabilities
- `c4-plugin`: System Map becomes a two-tab destination (Landscape and Views); the existing Landscape behavior, empty state, and controls remain unchanged inside the Landscape tab.

## Impact

- Backend, `plugins/c4`: a `View` model and migration, CRUD endpoints with pagination, a POST preview endpoint and a render-by-id endpoint beside the existing diagram endpoints, permissions for creating, editing, and deleting views, new plugin configuration for the node limit, tests for selection semantics, limits, uniqueness, and permissions.
- Frontend, `plugins/c4`: System Map page restructured into tabs, new list, detail, and editor pages and routes, a collapsible settings panel, a small generalization of the diagram viewer so it can show a fetched image and surface server errors; the Architecture tabs gain an entry button. The URL-state hook is removed.
- Entity picker: uses the existing per-kind list endpoints (name search, pagination, system filter); no dependency on the optional search plugin.
- Database: one new table in the `atlas.c4` plugin. No change to existing diagram endpoints, Landscape output, or other plugins.
- Documentation: the C4 feature page gains a section on views.
