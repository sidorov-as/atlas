## 1. Backend: configuration and settings contract

- [x] 1.1 Add the `maxNodes` setting to the `atlas.c4` plugin configuration with a default of 50, and document it
- [x] 1.2 Define the view settings schema (level, selection mode, `entities` UUIDs, depth as a positive integer or `all`, direction, entity types including actors, relationship source) as a JSON body schema shared by the preview endpoint and saved views; rendering options and format/download stay query parameters
- [x] 1.3 Re-check validation against the JSON body: empty selection, bad enum values, depth below one, mixed-level selections; ignore depth and direction in Selected entities only mode
- [x] 1.4 Define the JSON error body (machine-readable code and message) for 400 invalid parameters, 404 unknown or removed entity (naming it), and 422 node limit exceeded (limit and resulting count)

## 2. Backend: custom view builder

- [x] 2.1 Resolve selected entities, rejecting unknown, removed, or level-incompatible entities with an error that names them
- [x] 2.2 Build the level graph in memory: reuse declared relationships and the `consumesAPI`/`providesAPI`/`dependsOn` derived relations, apply the declared-only or declared-plus-derived filter and the declared-over-derived precedence
- [x] 2.3 Systems level: aggregate endpoints to Systems (actors stay themselves) before selection and traversal
- [x] 2.4 Components level: restrict nodes to Components, Resources, APIs, and actors; keep edges whose ends are both nodes
- [x] 2.5 Implement Selected entities only: nodes are exactly the selection, edges only between selected nodes, isolated nodes retained
- [x] 2.6 Implement Neighborhood: breadth-first traversal honoring depth (or unlimited), direction, and entity-type filters; excluded types are neither neighbors nor bridges; roots always visible
- [x] 2.7 Implement actors: discover actor kinds through the `architecture.actor.v1` capability, only via declared relationships, shown as leaves in Neighborhood unless they are roots, selectable as roots and members
- [x] 2.8 Enforce the node limit after selection and before PlantUML, excluding boundaries and decorative elements
- [x] 2.9 Emit the payload with the existing element and relationship helpers, semantic styling, and deterministic ordering; add System boundaries around visible elements at the Components level (none for Resources without a System)

## 3. Backend: diagram endpoints

- [x] 3.1 Add `POST diagrams/custom/` (preview of unsaved settings, SVG) taking the settings as a JSON body, reusing the authentication and `atlas.c4.diagram.read` checks
- [x] 3.2 Add `GET views/{id}/diagram/` with SVG default, PNG, download, and rendering options; unknown view id returns 404
- [x] 3.3 Remove the old `GET diagrams/custom/` route and its query-parameter parsing
- [x] 3.4 Map validation, not-found, limit, and render failures to the agreed statuses and JSON bodies
- [x] 3.5 Add the read-only actor kinds endpoint (`custom-view/actor-kinds/`) returning actor-capable kinds with labels, resolved via `architecture.actor.v1`, gated by authentication and `atlas.c4.diagram.read`
- [x] 3.6 Update the generated API reference or schema output for the new and removed endpoints

## 4. Backend: View model and API

- [x] 4.1 Add the `View` model to `atlas_plugin_c4` (UUID primary key, `name`, `description`, `settings` JSON, `created_at`, `updated_at`) with a migration and a `Lower(name)` unique constraint
- [x] 4.2 Verify that plugin composition picks up migrations for the `c4_plugin` app label and that the migration-lint workflow accepts the first migration of this plugin
- [x] 4.3 Register `atlas.c4.view.create` and `atlas.c4.view.delete`, check `atlas.c4.view.create` for updates, and document the suffix-based evaluator behavior next to the registration
- [x] 4.4 Add the endpoints: create, paginated list with name search and name sort (ascending default, descending), read (including missing entities), update, delete
- [x] 4.5 Validate settings on save with the shared schema and entity resolution; report a duplicate name as a validation error on the name field
- [x] 4.6 Rendering a saved view that references a removed entity returns the unknown-entity error naming it

## 5. Backend tests

- [x] 5.1 Selected-only semantics: edges between selected nodes only, isolated node kept, removal drops edges
- [x] 5.2 Neighborhood semantics: depth one and greater, each direction, system-level aggregation before depth, excluded types not bridging, roots surviving filters, unlimited depth
- [x] 5.3 Relationship source: declared only versus declared plus derived, declared superseding derived
- [x] 5.4 Actors: leaf behavior, disabled, root, selection member, no inference from ownership, Systems-level collapse of actor-to-Component edges
- [x] 5.5 Boundaries: only visible elements, one per System, Resource without a System outside any boundary
- [x] 5.6 Limit: below, at, above the limit, PlantUML not invoked above it, configuration override, unlimited depth rejected above it
- [x] 5.7 Validation and errors: empty selection, unknown entity named in the error, mixed levels, invalid parameters, unauthenticated and unauthorized requests
- [x] 5.8 Determinism and styling: identical output for repeated requests, Resource rendering by type
- [x] 5.9 Actor kinds endpoint: lists capability-declaring kinds only, includes a newly registered actor kind, rejects unauthenticated and unauthorized requests
- [x] 5.10 Preview endpoint: POST accepted, settings in the query string ignored, authentication and permission
- [x] 5.11 Saved view diagram endpoint: SVG, PNG, download, unknown id, removed entity
- [x] 5.12 View API: create, list pagination and search, read with missing entities, update, delete, required name, case-insensitive uniqueness, update keeping the own name, invalid settings
- [x] 5.13 Permissions: an authenticated non-owner can create, edit, and delete; read-only and unauthenticated users cannot; `atlas.c4.diagram.read` is required to read

## 6. Frontend: data layer

- [x] 6.1 Define the settings model and the API client for preview (POST), view CRUD, and saved view diagram URLs; remove the URL serialization of settings
- [x] 6.2 Remove the URL-state hook and its tests
- [x] 6.3 Generalize the diagram viewer additively so it can display a fetched image and report errors, using `fetch` with `AbortController` and an object URL; existing viewers keep current behavior
- [x] 6.4 Let the generalized viewer load from a POST preview as well as from a saved view URL
- [x] 6.5 Add a viewer-preferences key for the custom view
- [x] 6.6 Load actor kinds from the C4 actor kinds endpoint and use them in the picker when the Actors type is enabled
- [x] 6.7 Implement the entity picker data source over the per-kind list endpoints (name search, small pages, merged results with kind and System), without relying on the search plugin

## 7. Frontend: System Map and views UI

- [x] 7.1 Restructure the System Map page into Landscape and Views tabs; build the Views list on the pattern of `FlowsListPage` (search bar, table with Name and Description, name sort, pagination, Edit and Delete row actions with delete confirmation, Create view, empty state); keep Landscape unchanged
- [x] 7.2 Add the routes `/system-map/views/new`, `/system-map/views/:id`, and `/system-map/views/:id/edit` (new and edit as write routes) and keep the System Map navigation item active on them
- [x] 7.3 Build the view detail: viewer with SVG and PNG export, Edit, Delete with confirmation, not-found state, missing-entity warning, and actionable error messages
- [x] 7.4 Build the editor page: preview on the left, collapsible View settings panel on the right (open by default, same toggle as the flow editor), narrow-screen layout, Name and Description fields, Save, duplicate-name error on the Name field, and confirmation when leaving with unsaved changes
- [x] 7.5 Move the existing settings panel controls (Level, Selection, Relationships, entity types, Reset, Apply view) into the right-hand panel
- [x] 7.6 Entity multi-select: search, kind and System in results, no duplicates, stable identifiers, compact rows with kind icon and remove button, count in the heading, empty-state text
- [x] 7.7 Neighborhood controls, level switching with the "Selection cleared for the new level" notice, and entity-type rules
- [x] 7.8 Separate draft and applied state: Apply view only renders the preview, Save stores the draft; unapplied-changes notice; ignore stale responses; keep the previous preview on failure with Retry, the limit message, and removal of missing entities
- [x] 7.9 Remove the Copy link button and all URL and Back/Forward handling of settings
- [x] 7.10 Change "Open in view builder" on the System and Component Architecture tabs to link to `/system-map/views/new?root=<uuid>`; the editor resolves the root, derives the level, applies the defaults, renders immediately, and shows a message for an unknown root
- [x] 7.11 Apply responsive layout and accessibility (labelled fields, tooltip and `aria-label` on the panel toggle and other icon buttons, theme support)

## 8. Frontend tests

- [x] 8.1 Replace the URL serialization and hook tests with settings model and API client tests
- [x] 8.2 Draft versus applied behavior: editing does not fetch, Apply previews without saving, Save stores the draft, Reset changes the draft only, leaving with unsaved changes asks for confirmation
- [x] 8.3 Level switching clears entities and shows the notice; entity-type blocking hint; selection kept across mode switches
- [x] 8.4 Stale-response handling and failure retention of the previous preview with the POST preview
- [x] 8.5 Picker: kind and System shown, no duplicates, actors offered when enabled
- [x] 8.6 Views list (pagination, search, name sort, row Edit and Delete with confirmation, empty state), detail (Edit, Delete with confirmation, missing entity warning), editor (panel collapse and expand, required name, duplicate name, save)
- [x] 8.7 Entry points from the System and Component Architecture tabs produce `?root=` links; prefill behavior and unknown root
- [x] 8.8 Existing viewer tests and Landscape tests still pass unchanged

## 9. Documentation and verification

- [x] 9.1 Update the C4 feature documentation: Views list, editor, saving, sharing by the view page, levels, modes, actors, the node limit and its configuration, and the note that a view stores rules and entity ids rather than a snapshot
- [x] 9.2 Check that diagrams at the default `maxNodes` of 50 are readable on the demo catalog and a larger catalog; change the default only if they are not, and record the result
- [x] 9.3 Verify the booking example through a saved view: five selected entities with declared-only relationships give four relationships, and removing Booking Events leaves Notification Worker as an isolated node
- [x] 9.4 Visually verify the list, detail, and editor in a browser on wide and narrow screens in light and dark themes, with the panel collapsed and expanded
