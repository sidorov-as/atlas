## MODIFIED Requirements

### Requirement: Visual Flow step authoring

The Flow create/edit page SHALL provide the interactive node canvas as its primary way to author its `steps` array. The canvas SHALL allow an author to add, edit, retype, connect, reposition, remove, and — for a transition between two existing steps — edit or delete that transition independently of either endpoint step, all without editing JSON directly. Adding a step SHALL open a node-type picker offering Actor, Component, Data, API, System, Team, API Call, Event, External, and Step; selecting an entity-backed type SHALL show a catalog lookup scoped to that type's kind, selecting API Call or Event SHALL show a searchable lookup across Endpoint/Operation records, and selecting Step or External SHALL show fields for its own data (title, optional summary, an optional color, an optional icon, and an optional free-text type label for Step, or a label for External). The API Call and Event tiles SHALL render disabled, with a tooltip explaining that the APIs plugin is required, when the running distribution does not have `atlas.apis` installed. Clicking an existing node SHALL reopen the same modal pre-filled with that step's current data, with a "Change type" action that resets type-specific fields. Connecting two nodes by dragging from one node's connection handle to another SHALL set the source step's `next_step` or append to its `next_steps`. An author SHALL additionally be able to open the same node-type picker directly from an existing node — via that node's own add control, or via a placeholder shown only next to a step with no outgoing transition — and once a type is chosen, the new step SHALL be connected as that node's `next_step` (or appended to its `next_steps` if it already has one) and positioned adjacent to it, without requiring a separate drag-to-connect gesture. Every node's add and remove controls on the canvas SHALL remain visible at all times, not only while the node is hovered. Clicking an existing transition SHALL open a modal to edit its `label` or delete the transition, without removing either step it connects. The canvas SHALL preserve the persisted Flow `steps` JSON grammar (field names `entity_ref`, `external_label`, `query_ref`, `event_ref` are unchanged by the node-type picker's renamed tile labels) and SHALL submit the same Flow API payload as the JSON editor.

#### Scenario: Add an entity-backed step from the node-type picker

- **WHEN** an author activates Add Step, selects the Component type, and chooses a Component from the catalog lookup
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as a Component with that Component's actual subtype icon and color, and referencing the selected Component's canonical `component:name` ref

#### Scenario: Add an API Call step from the node-type picker

- **WHEN** an author activates Add Step, selects the API Call type, and chooses an Endpoint from its search lookup
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as an API Call showing that Endpoint's method on its chip, and storing that Endpoint's `query_ref` (its owning API, id, and snapshotted method/path)

#### Scenario: Add an Event step from the node-type picker

- **WHEN** an author activates Add Step, selects the Event type, and chooses an Operation from its search lookup
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as an Event showing that Operation's direction on its chip, and storing that Operation's `event_ref` (its owning API, id, and snapshotted direction/channel)

#### Scenario: API Call and Event tiles are disabled when atlas.apis is absent

- **WHEN** an author activates Add Step in a distribution that does not have `atlas.apis` installed
- **THEN** the API Call and Event tiles render disabled, with a tooltip explaining that the APIs plugin is required, and cannot be selected

#### Scenario: Add a plain Step node with a color, icon, and type label

- **WHEN** an author activates Add Step, selects the Step type, chooses a color, optionally picks an icon, and optionally enters a type label
- **THEN** a new node is added styled with the chosen color on its border and type chip, showing the chosen icon (or the default Step icon if none was picked), showing the entered type label on its chip (or "Step" if none was entered), and no `entity_ref`

#### Scenario: Add an External node

- **WHEN** an author activates Add Step, selects the External type, and enters a label
- **THEN** a new node is added styled as External, storing that label and no `entity_ref`, and the External tile's help text explains that this represents a step with no catalog record at all

#### Scenario: Retype an existing node

- **WHEN** an author clicks an existing Component node, activates "Change type", and selects Data, then chooses a Resource from the catalog lookup
- **THEN** the step's `entity_ref` is replaced with the selected Resource's reference and the node re-renders styled as Data

#### Scenario: Connect two nodes by dragging

- **WHEN** an author drags from one node's connection handle and drops it on another node
- **THEN** the source step's transition is updated to target the dropped-on step, and the canvas renders a connection between them

#### Scenario: Add a step directly from an existing node's own add control

- **WHEN** an author activates a node's own add control, selects a type, and completes the node-type picker
- **THEN** the new step is connected as that node's `next_step` (or appended to `next_steps` if it already has one) and positioned adjacent to it on the canvas, with no separate drag-to-connect gesture needed

#### Scenario: Add a step from a childless step's add-next placeholder

- **WHEN** an author activates the add-next placeholder shown next to a step with no outgoing transition, and completes the node-type picker
- **THEN** the new step is connected and positioned exactly as activating that step's own add control would, and the placeholder no longer renders for that step once it has an outgoing transition

#### Scenario: Node add and remove controls remain visible without hovering

- **WHEN** an author views the canvas without hovering any node
- **THEN** every node's add and remove controls are visible, not only the node currently under the pointer

#### Scenario: Edit a transition's label

- **WHEN** an author clicks an existing transition on the canvas and changes its label in the opened modal
- **THEN** the corresponding `next_step.label` or `next_steps[]` entry's `label` is updated and the new label renders on the connection

#### Scenario: Delete a transition without deleting either step

- **WHEN** an author clicks an existing transition on the canvas and activates Delete in the opened modal
- **THEN** the transition is removed from the source step's `next_step`/`next_steps`, the connection no longer renders, and both the source and target steps remain on the canvas

#### Scenario: Remove a node

- **WHEN** an author removes a node from the canvas
- **THEN** the editor removes transitions to that step's id and does not leave a transition targeting a nonexistent id

### Requirement: Unified node visual styling

Every node kind on the canvas SHALL render with one consistent card anatomy: a neutral, theme-aware card fill; plain, uncolored title and subtitle text; a bold (2px) colored border carrying the kind's identity color; and a small colored chip showing the kind's icon and label. No node kind SHALL use a tinted or kind-colored card fill, and no node kind SHALL color its own title or subtitle text. The chip and title SHALL render at the same fixed vertical position within the card regardless of whether a subtitle is present — a card with no subtitle SHALL leave the resulting empty space below the title, and SHALL NOT re-center its chip and title as a block. Entity-backed kinds Actor, Team, Data, and System, and External, SHALL use a fixed color per kind and a fixed chip label naming the kind. Component and API SHALL use the color and icon of the referenced entity's actual subtype (Component: service/website/library/worker; API: openapi/grpc/asyncapi/graphql), falling back to a neutral default only when the reference does not resolve. API Call and Event SHALL use a color derived from the step's snapshotted HTTP method / direction respectively, and SHALL show that resolved method (e.g. "GET", "POST") or direction (title-cased "Send"/"Receive") as their chip label, falling back to the generic "API Call"/"Event" label only when the reference is unresolved. Step SHALL use the author's chosen per-instance color, applied consistently to both its border and its chip, and SHALL show the author's chosen type label on its chip, falling back to "Step" when no type label is set.

#### Scenario: Entity-backed node renders with neutral fill and colored border

- **WHEN** a Data node is rendered on the canvas
- **THEN** its card fill is the shared neutral background, its title and subtitle render in plain (uncolored) text, and its border and type chip render in Data's fixed color

#### Scenario: Component node shows its real subtype's icon and color

- **WHEN** a Component node referencing a `worker`-typed Component is rendered on the canvas
- **THEN** its border and type chip render in the color and icon associated with the `worker` Component type, not the color/icon of any other Component type

#### Scenario: API node shows its real subtype's icon and color

- **WHEN** an API node referencing a `grpc`-typed API is rendered on the canvas
- **THEN** its border and type chip render in the color and icon associated with the `grpc` API type, not a single generic API color/icon shared by every API type

#### Scenario: Step node's chosen color drives both its border and its chip

- **WHEN** a Step node with an author-chosen color is rendered on the canvas
- **THEN** its border and its type chip both render in that chosen color, and its card fill remains the shared neutral background

#### Scenario: Step node's chip shows a custom type label

- **WHEN** a Step node with an author-chosen type label of "Retry" is rendered on the canvas
- **THEN** its type chip shows "Retry" instead of "Step", and its title/subtitle/border/fill render unchanged

#### Scenario: Step node with no type label falls back to "Step"

- **WHEN** a Step node with no `type_label` set (or one that is blank/whitespace-only) is rendered on the canvas
- **THEN** its type chip shows "Step"

#### Scenario: API Call node's border and chip reflect its snapshotted method

- **WHEN** an API Call node with a snapshotted `POST` method is rendered on the canvas
- **THEN** its border and type chip render in the color associated with `POST`, its type chip shows the text "POST", and its card fill remains the shared neutral background

#### Scenario: Event node's border and chip reflect its snapshotted direction

- **WHEN** an Event node with a snapshotted `send` direction is rendered on the canvas
- **THEN** its border and type chip render in the color associated with `send`, and its type chip shows the text "Send"

#### Scenario: A card's chip and title hold position whether or not a subtitle is present

- **WHEN** a Step node with a summary and a Step node without a summary are both rendered on the canvas
- **THEN** both nodes' chip and title render at the same vertical offset from the top of their card, and only the node without a summary shows empty space below its title

### Requirement: Catalog entity lookup for Flow steps

The node-type picker and edit modal SHALL provide a searchable catalog lookup for a step's `entity_ref`, scoped to the kind matching the selected node type (Actor → User, Team → Group, Component → Component, Data → Resource, API → API, System → System). The lookup SHALL store the selected entity's canonical `kind:name` reference. An author SHALL be able to clear the reference, which reverts the node to the plain Step type.

#### Scenario: Select a component reference

- **WHEN** an author selects the Component type and searches for and selects a Component in its entity lookup
- **THEN** the step stores that Component's canonical `component:name` reference and the node renders styled as a Component, using that Component's actual subtype icon and color

#### Scenario: Clear a reference

- **WHEN** an author clears a step's entity lookup
- **THEN** the step's `entity_ref` is removed and the node reverts to the plain Step type

### Requirement: Endpoint/Operation search lookup for API Call/Event steps

The API Call and Event tiles' lookup SHALL be a single flat search-as-you-type field across every API's Endpoints/Operations, rather than a two-stage "pick an API, then pick within it" flow. Each search result SHALL display the Endpoint/Operation's own identity (method and path, or channel) as its primary text and its owning API's name as secondary text. Selecting a result SHALL store its `query_ref`/`event_ref` on the step, including a snapshot of its display fields at the time of selection. An author SHALL be able to clear the reference, which reverts the node to the plain Step type.

#### Scenario: Search across all APIs' endpoints in one field

- **WHEN** an author types a query into the API Call tile's lookup that matches Endpoints belonging to more than one API
- **THEN** matching Endpoints from every matching API are shown in one flat result list, each showing its method/path and its owning API's name

#### Scenario: Selecting a search result stores the reference and snapshot

- **WHEN** an author selects an Endpoint from the API Call tile's search results
- **THEN** the step's `query_ref` stores that Endpoint's owning API, id, and its current method/path as a snapshot

#### Scenario: Clear an API Call/Event reference

- **WHEN** an author clears a step's API Call or Event lookup
- **THEN** the step's `query_ref`/`event_ref` is removed and the node reverts to the plain Step type

## ADDED Requirements

### Requirement: Stale Endpoint/Operation reference indicator

An API Call or Event node whose resolved Endpoint/Operation currently has `status: removed`, or whose resolved Endpoint currently has `deprecated: true`, SHALL show a warning icon on its card with a tooltip explaining that the reference is stale and naming which condition applies. This indicator SHALL be read-only: it SHALL NOT modify, clear, or remove the step's stored `query_ref`/`event_ref`, and SHALL NOT remove or alter the node itself. A node whose reference cannot be resolved this way (e.g. the APIs plugin is not installed) SHALL render without the indicator rather than erroring.

#### Scenario: API Call node warns when its Endpoint has been removed

- **WHEN** an API Call node's `query_ref` resolves to an Endpoint whose current `status` is `removed`
- **THEN** the node shows a warning icon with a tooltip explaining the Endpoint was removed, and its stored `query_ref` is unchanged

#### Scenario: API Call node warns when its Endpoint is deprecated

- **WHEN** an API Call node's `query_ref` resolves to an Endpoint whose current `deprecated` flag is `true`
- **THEN** the node shows a warning icon with a tooltip explaining the Endpoint is deprecated

#### Scenario: Event node warns when its Operation has been removed

- **WHEN** an Event node's `event_ref` resolves to an Operation whose current `status` is `removed`
- **THEN** the node shows a warning icon with a tooltip explaining the Operation was removed, and its stored `event_ref` is unchanged

#### Scenario: No warning when the reference is current

- **WHEN** an API Call or Event node's reference resolves to an Endpoint/Operation that is `active` and not deprecated
- **THEN** no warning icon is shown
