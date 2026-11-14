# c4-custom-view-diagram Specification

## Purpose

Defines how the C4 plugin builds PlantUML-backed diagrams over a user-chosen slice of the catalog, at the Systems or Components level, from selected entities or a depth- and direction-limited neighborhood. Covers the settings contract and its validation, the preview endpoint, the stored view model with its CRUD API and permissions, rendering a saved view by id, and the node-limit and error behavior shared by both rendering paths.

## Requirements

### Requirement: Custom view diagrams are served by a preview endpoint and by saved view id
The `atlas.c4` plugin SHALL provide two ways to generate a PlantUML-backed C4 diagram from a selection of catalog entities: a preview endpoint that accepts the view settings as a JSON request body and serves the SVG of that unsaved selection, and a saved view diagram endpoint that serves the diagram of a stored view by its id, with SVG by default, PNG through an explicit format parameter, and attachment disposition through a download parameter, equivalent to existing diagram endpoints. Both SHALL accept the same rendering options as existing diagram endpoints as query parameters, SHALL require an authenticated session and the `atlas.c4.diagram.read` permission, and SHALL NOT apply per-entity access checks to the entities in the selection. View settings SHALL NOT be accepted as query parameters.

#### Scenario: Default response is SVG
- **WHEN** an authenticated user with diagram read permission requests a saved view diagram without a format parameter
- **THEN** the endpoint returns generated `image/svg+xml` content

#### Scenario: PNG download is supported for a saved view
- **WHEN** an authenticated user requests a saved view diagram with `format=png` and download enabled
- **THEN** the endpoint returns an `image/png` attachment

#### Scenario: Preview of an unsaved draft
- **WHEN** an authenticated user with diagram read permission posts valid settings to the preview endpoint
- **THEN** the endpoint returns generated `image/svg+xml` content and no view is stored

#### Scenario: Settings in the query string are not accepted
- **WHEN** a request passes level, entities, or other view settings as query parameters
- **THEN** they have no effect on the diagram

#### Scenario: Unknown view id
- **WHEN** a user requests the diagram of a view id that does not exist
- **THEN** the endpoint returns a not-found error and renders nothing

#### Scenario: Unauthenticated request is rejected before rendering
- **WHEN** a request without an authenticated session requests a preview or a saved view diagram
- **THEN** the request is rejected and no diagram is rendered

#### Scenario: Missing permission is rejected
- **WHEN** an authenticated user without `atlas.c4.diagram.read` requests a preview or a saved view diagram
- **THEN** the request is rejected and no diagram is rendered

### Requirement: Custom views are built at either the Systems or the Components level
A custom view request SHALL name exactly one level. At the Systems level the selectable entities SHALL be Systems, plus actors when actors are enabled. At the Components level the selectable entities SHALL be Components, Resources, and APIs, plus actors when actors are enabled. A selection that mixes Systems with Components, Resources, or APIs SHALL be rejected with a client error before rendering.

#### Scenario: Systems level accepts Systems
- **WHEN** a request names the Systems level and selects two Systems
- **THEN** the endpoint generates a system-level diagram for those Systems

#### Scenario: Components level accepts entities from different Systems
- **WHEN** a request names the Components level and selects a Component, an API, and a Resource that belong to different Systems
- **THEN** the endpoint generates a component-level diagram containing all three

#### Scenario: Mixed selection is rejected
- **WHEN** a request selects a System together with a Component
- **THEN** the endpoint returns a client error naming the incompatible selection and renders nothing

### Requirement: Selected entities only mode shows exactly the chosen nodes
In Selected entities only mode, for a selected set S, the visible nodes SHALL be exactly S and the visible edges SHALL be the permitted relationships whose source and target are both in S. Isolated selected entities SHALL remain visible. No neighbors SHALL be added, and depth and direction SHALL have no effect.

#### Scenario: Only relationships between selected entities are drawn
- **WHEN** a selection contains Booking API, Booking DB, and Payment Service, and Booking API also has a relationship to an unselected Notification Worker
- **THEN** the diagram shows the three selected entities and the relationships among them, and does not show Notification Worker or its relationship

#### Scenario: Isolated selected entity stays visible
- **WHEN** a selected entity has no permitted relationship to any other selected entity
- **THEN** the diagram still shows it as an unconnected node

#### Scenario: Removing an entity removes its edges
- **WHEN** an entity is removed from the selection
- **THEN** the diagram no longer shows that node or any relationship that had it as an endpoint

### Requirement: Neighborhood mode expands roots by depth and direction
In Neighborhood mode the endpoint SHALL traverse the relationship graph of the chosen level from every root entity, honoring a positive integer depth (or unlimited depth) and a direction of both, outgoing, or incoming. Outgoing SHALL follow edges from source to target; incoming SHALL follow them from target to source. Depth SHALL count edges in the graph of the chosen level: at the Systems level, relationships SHALL first be aggregated to Systems and traversal SHALL then run on the aggregated graph. The result SHALL contain the roots, the entities reached, and the permitted relationships among them. Entity types excluded by the entity-type filter SHALL NOT be added as neighbors and SHALL NOT serve as intermediate hops. Roots SHALL remain visible regardless of the entity-type filter.

#### Scenario: Depth one shows direct neighbors
- **WHEN** a Neighborhood request has one root, depth 1, and direction both
- **THEN** the diagram contains the root, every entity directly connected to it by a permitted relationship in either direction, and the permitted relationships among them

#### Scenario: Outgoing direction follows edge direction only
- **WHEN** a Neighborhood request has direction outgoing and the root has both callers and callees
- **THEN** only entities reachable by following relationships from source to target appear

#### Scenario: Depth counts system-level hops
- **WHEN** a Systems-level Neighborhood request has depth 2
- **THEN** traversal runs on the System-aggregated graph, so Systems up to two aggregated relationships away from the root appear

#### Scenario: Excluded types are not bridges
- **WHEN** a Components-level Neighborhood request excludes Resources and a Resource is the only connection between the root and another Component
- **THEN** that Component is not reached through the Resource

#### Scenario: Roots survive type filters
- **WHEN** a selected root is a Resource and the Resources entity type is disabled
- **THEN** the root remains visible

#### Scenario: Unlimited depth is still bounded by the node limit
- **WHEN** a Neighborhood request uses unlimited depth and the reachable set exceeds the node limit
- **THEN** the endpoint rejects the request with the node-limit error instead of rendering

### Requirement: Relationship source filter reuses existing relationship rules
A custom view request SHALL choose between declared relationships only and declared plus derived relationships. Declared relationships SHALL be the Architecture Relationships. Derived relationships SHALL be the catalog interactions the existing diagrams derive (`consumesAPI`, `providesAPI`, and `dependsOn`), labelled as in existing diagrams. When both sources are enabled, a declared relationship SHALL supersede a derived one with the same directed visible endpoints. The endpoint SHALL NOT add separate merge or simplification options.

#### Scenario: Declared only hides derived edges
- **WHEN** two selected entities are connected only by a derived `dependsOn` relation and the request chooses declared only
- **THEN** the diagram shows both entities without a relationship between them

#### Scenario: Declared supersedes derived
- **WHEN** both a declared relationship and a derived relation connect the same directed pair and the request chooses declared plus derived
- **THEN** the diagram shows the declared relationship with its label and technology, and not the derived one

### Requirement: Actors are optional, declared-only, and leaves in neighborhoods
Actors SHALL be the entities whose kinds declare the `architecture.actor.v1` capability. A custom view request SHALL be able to enable or disable actors. An actor SHALL appear only through a declared Architecture Relationship and SHALL NOT be inferred from ownership or membership. Actors SHALL be selectable as members of a Selected entities only selection and as Neighborhood roots. In Neighborhood mode an actor adjacent to a visited non-actor entity SHALL be shown when actors are enabled but SHALL NOT be used to reach further entities unless it is itself a root. At the Systems level, a declared relationship between an actor and a Component SHALL be shown as a relationship between the actor and the Component's System.

#### Scenario: Actor appears as a leaf neighbor
- **WHEN** a Neighborhood request has actors enabled and a visited System has a declared relationship with an actor that is also connected to other Systems
- **THEN** the actor appears, and the other Systems are not added through it

#### Scenario: Actors disabled
- **WHEN** a Neighborhood request disables actors
- **THEN** no actor appears in the diagram, including actors that were declared as related to a visited entity

#### Scenario: Actor as root
- **WHEN** an actor is selected as a Neighborhood root
- **THEN** traversal starts from the actor and reaches the entities it declares relationships with

#### Scenario: Ownership does not create actors
- **WHEN** a Group owns a selected entity but has no declared Architecture Relationship
- **THEN** the Group does not appear in the diagram

### Requirement: Actor kinds are available through a C4 API endpoint
The `atlas.c4` plugin API SHALL provide a read-only endpoint that lists the entity kinds that are actors, each with its kind identifier and display label, resolved through the `architecture.actor.v1` capability. The endpoint SHALL require an authenticated session and the `atlas.c4.diagram.read` permission. The custom view endpoint SHALL use the same resolution when validating selections.

#### Scenario: Endpoint lists actor-capable kinds
- **WHEN** an authenticated user with diagram read permission requests the actor kinds and the registered `actor` and `group` kinds declare the capability
- **THEN** the response contains `actor` and `group` with their labels and no kind that lacks the capability

#### Scenario: A newly registered actor kind is included
- **WHEN** a plugin registers a kind that declares `architecture.actor.v1`
- **THEN** the actor kinds endpoint includes it and the custom view endpoint accepts entities of that kind as actors

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request without an authenticated session requests the actor kinds
- **THEN** the request is rejected

### Requirement: Components-level views draw System boundaries around visible elements only
At the Components level the diagram SHALL group visible Components, Resources, and APIs by their owning System in a boundary frame per System. A boundary SHALL contain only elements that are visible in the diagram and SHALL NOT cause other elements of that System to be added. A Resource with no System SHALL be drawn outside any boundary. Boundary frames and other decorative elements SHALL NOT count toward the node limit.

#### Scenario: Boundary contains only visible elements
- **WHEN** a Components-level view shows one of three Components of a System
- **THEN** the System's boundary contains that Component only

#### Scenario: Entities from several Systems get separate boundaries
- **WHEN** a Components-level view shows elements from two Systems
- **THEN** the diagram draws one boundary per System around its visible elements

#### Scenario: Resource without a System has no boundary
- **WHEN** a Components-level view shows a Resource that belongs to no System
- **THEN** the Resource is drawn outside any System boundary

### Requirement: Custom views enforce a configurable node limit before rendering
The `atlas.c4` plugin SHALL provide a plugin configuration setting for the maximum number of visible nodes for custom views, with a default of 50. The endpoint SHALL evaluate the limit after selection and before invoking PlantUML, and SHALL NOT truncate the result. When the limit is exceeded the endpoint SHALL respond with a distinguishable client error whose JSON body states the limit and the resulting node count and indicates that reducing depth or the selection resolves it.

#### Scenario: Result within the limit renders
- **WHEN** a request resolves to a number of nodes at or below the limit
- **THEN** the endpoint renders the diagram

#### Scenario: Result above the limit is rejected without rendering
- **WHEN** a request resolves to more nodes than the limit
- **THEN** the endpoint responds with the node-limit error and PlantUML is not invoked

#### Scenario: Default limit is 50
- **WHEN** the `atlas.c4` plugin configuration does not set the maximum node count
- **THEN** the endpoint applies a limit of 50 nodes

#### Scenario: Limit is configurable
- **WHEN** an operator sets the maximum node count in the `atlas.c4` plugin configuration
- **THEN** the endpoint applies that value instead of the default

### Requirement: Custom view requests are validated and never silently altered
The endpoints SHALL validate all view settings, whether they arrive in a preview request or are stored in a saved view. A request with an empty selection, an unknown or invalid level, selection mode, direction, relationship source, depth, or entity type SHALL be rejected with a client error. A request that references an entity that does not exist, has been removed, or is not selectable at the chosen level SHALL be rejected with an error identifying that entity, and the endpoint SHALL NOT omit it silently. Saving a view whose settings reference such an entity SHALL be rejected the same way. Error responses SHALL carry a JSON body with a machine-readable code and a human-readable message.

#### Scenario: Empty selection is rejected
- **WHEN** a request contains no entities
- **THEN** the endpoint returns a client error and renders nothing

#### Scenario: Unknown entity is reported
- **WHEN** a request references an entity identifier that does not exist
- **THEN** the endpoint returns a not-found error identifying that identifier and renders nothing

#### Scenario: Invalid parameter is rejected
- **WHEN** a request has a depth of zero or a direction other than both, outgoing, or incoming
- **THEN** the endpoint returns a client error naming the invalid parameter

#### Scenario: Selection-only parameters are ignored for Selected entities only
- **WHEN** a Selected entities only request also carries depth and direction values
- **THEN** the diagram is generated as if they were absent

#### Scenario: Saving a view with an unknown entity is rejected
- **WHEN** a client saves a view whose settings reference an entity that does not exist
- **THEN** the API returns an error identifying that entity and stores nothing

### Requirement: Custom view diagrams use the existing semantic styling
Custom view diagrams SHALL use the same element types, tags, relationship styling, legend, and configurable semantic styling as existing C4 diagrams, including external-element styling and Resource rendering by catalog type. Output for the same catalog state and request SHALL be deterministic.

#### Scenario: Resource rendering follows its catalog type
- **WHEN** a Components-level view contains a `database` Resource and a `queue` Resource
- **THEN** they render as `ComponentDb` and `ComponentQueue` respectively

#### Scenario: Same request gives identical output
- **WHEN** the same custom view is requested twice without catalog changes
- **THEN** both responses contain the same diagram content

### Requirement: Views are saved objects with a unique name
A View SHALL have an id (UUID), a required name of at most 255 characters, an optional description, settings (level, selection mode, entities, depth, direction, entity types, and relationship source), and created and updated timestamps. Names SHALL be unique ignoring case, and a duplicate SHALL be rejected with a validation error on the name. Settings SHALL be validated by the same rules as a preview request.

#### Scenario: Create a view
- **WHEN** a user saves valid settings with a new name and an optional description
- **THEN** a view with a generated UUID is stored and returned

#### Scenario: Name is required
- **WHEN** a user saves a view with an empty name
- **THEN** the API returns a validation error on the name and stores nothing

#### Scenario: Duplicate name differing only in case is rejected
- **WHEN** a view named "Billing" exists and a user saves another view named "billing"
- **THEN** the API returns a validation error on the name and stores nothing

#### Scenario: Keeping the own name on update
- **WHEN** a user updates a view without changing its name
- **THEN** the update succeeds

#### Scenario: Invalid settings are rejected
- **WHEN** a user saves a view with an empty selection or a depth of zero
- **THEN** the API returns a validation error and stores nothing

### Requirement: Saved views have list, read, update, and delete endpoints
The `atlas.c4` plugin API SHALL provide create, list, read, update, and delete endpoints for views. The list SHALL be paginated, SHALL support searching by name, and SHALL be ordered by name ascending by default, with descending name order available. No other sort order is required. Reading a view SHALL include the settings and identify the referenced entities that no longer exist. Deleting a view SHALL NOT affect catalog entities.

#### Scenario: List is paginated
- **WHEN** more views exist than fit on one page
- **THEN** the list returns one page with the total count and the means to request the others

#### Scenario: Search by name
- **WHEN** a user lists views with a name search
- **THEN** only views whose name matches are returned

#### Scenario: Sort by name
- **WHEN** a user lists views sorted by name descending
- **THEN** the views are returned in reverse name order

#### Scenario: Read reports missing entities
- **WHEN** a user reads a view that references a removed entity
- **THEN** the response contains the view and identifies the missing entity

#### Scenario: Update replaces the stored values
- **WHEN** a user updates a view with a new name, description, and settings
- **THEN** the stored view reflects them and its updated timestamp changes

#### Scenario: Delete removes the view only
- **WHEN** a user deletes a view
- **THEN** the view is gone and the entities it referenced are unchanged

### Requirement: Saved views are shared and writable by authenticated users
Reading and rendering views SHALL require the `atlas.c4.diagram.read` permission. Creating, updating, and deleting views SHALL be allowed to any authenticated user who is not read-only, through permissions registered by the plugin, independently of entity ownership. Views SHALL be visible to every user who can read diagrams.

#### Scenario: Another user edits a view
- **WHEN** an authenticated user who did not create a view updates or deletes it
- **THEN** the change is allowed

#### Scenario: Read-only user cannot write
- **WHEN** a read-only user tries to create, update, or delete a view
- **THEN** the request is rejected and nothing changes

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request without an authenticated session reads or writes views
- **THEN** the request is rejected

### Requirement: Saved views with removed entities fail loudly
Rendering a saved view that references an entity that no longer exists SHALL return the unknown-entity error identifying that entity and SHALL NOT draw a partial diagram. The stored view SHALL remain readable and editable so that the reference can be removed.

#### Scenario: Entity removed after the view was saved
- **WHEN** a catalog entity referenced by a saved view is deleted and the view diagram is requested
- **THEN** the endpoint returns the unknown-entity error naming that entity and renders nothing

#### Scenario: Repairing the view
- **WHEN** a user removes the missing entity from the view and saves
- **THEN** the view renders again

### Requirement: Custom view diagrams accept an optional theme
The custom view preview endpoint and the saved-view diagram endpoint SHALL accept the same optional `theme` option (`light` or `dark`, default `light`) as the other C4 diagram endpoints, including for SVG, PNG, and download requests. A dark custom view diagram SHALL keep the same element types, tags, relationship styling, and legend entries as its light rendering, differing only in palette. The `theme` option SHALL NOT be part of a saved view's settings.

#### Scenario: Saved view renders in dark
- **WHEN** an authenticated user requests a saved view's diagram with `theme=dark`
- **THEN** the endpoint returns that view's diagram rendered with the dark palette

#### Scenario: Preview renders in dark
- **WHEN** an authenticated user requests a preview with valid settings and `theme=dark`
- **THEN** the endpoint returns the preview rendered with the dark palette

#### Scenario: Theme is not stored on the view
- **WHEN** a user saves a view while the UI is in dark mode
- **THEN** the stored view settings contain no theme value, and the same view renders light or dark according to each request

#### Scenario: Default stays light
- **WHEN** a custom view diagram is requested without `theme`
- **THEN** the response is identical to that before the option existed
