# visual-flow-editor Specification

## Purpose

Visual authoring for persisted Flow steps while retaining direct JSON editing.

## Requirements

### Requirement: Visual Flow step authoring

The Flow create/edit page SHALL provide the interactive node canvas as its primary way to author its `steps` array. The canvas SHALL allow an author to add, edit, retype, connect, reposition, remove, and — for a transition between two existing steps — edit or delete that transition independently of either endpoint step, all without editing JSON directly. Adding a step SHALL open a node-type picker offering Actor, Component, Data, API, System, Team, API Call, Event, External, Step, Flow, and Link; selecting an entity-backed type or Flow SHALL show a searchable lookup scoped to that type (Actor/Team/Component/Data/API/System against the catalog, Flow against existing Flows), selecting API Call or Event SHALL show a searchable lookup across Endpoint/Operation records, and selecting Step, External, or Link SHALL show fields for its own data (title, optional summary, an optional color, an optional icon, and an optional free-text type label for Step; a label for External; an optional title, an optional summary, and a URL for Link). The API Call and Event tiles SHALL render disabled, with a tooltip explaining that the APIs plugin is required, when the running distribution does not have `atlas.apis` installed. Clicking an existing node SHALL reopen the same modal pre-filled with that step's current data, with a "Change type" action that resets type-specific fields. Connecting two nodes by dragging from one node's connection handle to another SHALL set the source step's `next_step` or append to its `next_steps`. An author SHALL additionally be able to open the same node-type picker directly from an existing node — via that node's own add control, or via a placeholder shown only next to a step with no outgoing transition — and once a type is chosen, the new step SHALL be connected as that node's `next_step` (or appended to its `next_steps` if it already has one) and positioned adjacent to it, without requiring a separate drag-to-connect gesture. Every node's add and remove controls on the canvas SHALL remain visible at all times, not only while the node is hovered. Clicking an existing transition SHALL open a modal to edit its `label` or delete the transition, without removing either step it connects. The canvas SHALL preserve the persisted Flow `steps` JSON grammar (field names `entity_ref`, `external_label`, `query_ref`, `event_ref`, `flow_ref`, `link_url` are unchanged by the node-type picker's renamed tile labels) and SHALL submit the same Flow API payload as the JSON editor.

#### Scenario: Add an entity-backed step from the node-type picker

- **WHEN** an author activates Add Step, selects the Component type, and chooses a Component from the catalog lookup
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as a Component with that Component's actual subtype icon and color, and referencing the selected Component's canonical `component:name` ref

#### Scenario: Add an API Call step from the node-type picker

- **WHEN** an author activates Add Step, selects the API Call type, and chooses an Endpoint from its search lookup
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as an API Call showing that Endpoint's method on its chip, and storing that Endpoint's `query_ref` (its owning API, id, and snapshotted method/path)

#### Scenario: Add an Event step from the node-type picker

- **WHEN** an author activates Add Step, selects the Event type, and chooses an Operation from its search lookup
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as an Event showing that Operation's direction on its chip, and storing that Operation's `event_ref` (its owning API, id, and snapshotted direction/channel)

#### Scenario: Add a Flow step from the node-type picker

- **WHEN** an author activates Add Step, selects the Flow type, and chooses a Flow from its search lookup
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as a Flow node, and storing the selected Flow's id as `flow_ref`

#### Scenario: Add a Link step from the node-type picker

- **WHEN** an author activates Add Step, selects the Link type, enters a URL, and optionally a title and summary
- **THEN** a new node is added to the canvas with a fresh non-colliding id, styled as a Link node, storing the entered URL as `link_url` and any entered title/summary

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

Every node kind on the canvas SHALL render with one consistent card anatomy: a neutral, theme-aware card fill; plain, uncolored title and subtitle text; a bold (2px) colored border carrying the kind's identity color; and a small colored chip showing the kind's icon and label. No node kind SHALL use a tinted or kind-colored card fill, and no node kind SHALL color its own title or subtitle text. The chip and title SHALL render at the same fixed vertical position within the card regardless of whether a subtitle is present — a card with no subtitle SHALL leave the resulting empty space below the title, and SHALL NOT re-center its chip and title as a block. Entity-backed kinds Actor, Team, Data, and System, External, Flow, and Link SHALL use a fixed color per kind and a fixed chip label naming the kind. Component and API SHALL use the color and icon of the referenced entity's actual subtype (Component: service/website/library/worker; API: openapi/grpc/asyncapi/graphql), falling back to a neutral default only when the reference does not resolve. API Call and Event SHALL use a color derived from the step's snapshotted HTTP method / direction respectively, and SHALL show that resolved method (e.g. "GET", "POST") or direction (title-cased "Send"/"Receive") as their chip label, falling back to the generic "API Call"/"Event" label only when the reference is unresolved. Step SHALL use the author's chosen per-instance color, applied consistently to both its border and its chip, and SHALL show the author's chosen type label on its chip, falling back to "Step" when no type label is set.

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

#### Scenario: Flow and Link nodes use their own fixed color and chip label

- **WHEN** a Flow node and a Link node are both rendered on the canvas
- **THEN** each renders with its own fixed border/chip color, distinct from one another, and each chip shows a fixed label naming its kind ("Flow" or "Link") — as with the existing fixed-color kinds (e.g. Actor and Team already share one color), a fixed kind's color is not guaranteed unique across every other kind, only constant for that kind and compliant with the picker's own no-adjacent-color rule

#### Scenario: A card's chip and title hold position whether or not a subtitle is present

- **WHEN** a Step node with a summary and a Step node without a summary are both rendered on the canvas
- **THEN** both nodes' chip and title render at the same vertical offset from the top of their card, and only the node without a summary shows empty space below its title

### Requirement: Catalog entity lookup for Flow steps

The node-type picker and edit modal SHALL provide a searchable catalog lookup for a step's `entity_ref`, scoped to the kind matching the selected node type (Actor → User, Team → Group, Component → Component, Data → Resource, API → API, System → System). The lookup SHALL store the selected entity's canonical `kind:name` reference. An author SHALL be able to clear the reference, which reverts the node to the plain Step type. For an entity-backed step, the modal SHALL NOT show editable Title or Summary fields — the node's card SHALL always render the referenced entity's current `title` as its title (falling back to the entity's raw name, then to the step's own id, when the resolved title is unavailable) and the entity's current `description` as its subtitle, resolved live and never taken from any value stored on the step itself. A step carrying a non-empty `entity_ref` together with a non-empty `title` or `summary` SHALL be rejected on save.

The lookup's dropdown SHALL render each match as one shared item row — an icon, the entity's primary display text, and secondary text identifying its kind — using the same row shape and the same loading-state treatment as the Endpoint/Operation lookup used for API Call/Event steps (see "Endpoint/Operation search lookup for API Call/Event steps"), so an author moving between step kinds within the same modal sees one consistent lookup control rather than a different shape per kind.

A just-added entity-backed step's node SHALL settle on a single title/subtitle without visibly changing between two different guesses as data resolves: if the referenced entity's live title/description is not yet available at first render, the node SHALL either wait to render its title/subtitle until that data resolves, or render a value that will not change once the data resolves — an author SHALL NOT see the node's title change to a different value shortly after the step is added.

#### Scenario: Select a component reference

- **WHEN** an author selects the Component type and searches for and selects a Component in its entity lookup
- **THEN** the step stores that Component's canonical `component:name` reference, and the node renders styled as a Component, using that Component's actual subtype icon and color

#### Scenario: Clear a reference

- **WHEN** an author clears a step's entity lookup
- **THEN** the step's `entity_ref` is removed, and the node reverts to the plain Step type

#### Scenario: Selecting an entity does not offer Title/Summary fields to edit

- **WHEN** an author selects a reference for an entity-backed step (Actor, Team, Component, Data, API, or System) in the node-type picker or edit modal
- **THEN** no Title or Summary input is shown for that step; the modal offers no way to type custom text for it

#### Scenario: Entity-backed node renders the referenced entity's live title and description

- **WHEN** an entity-backed step's node is rendered, and the referenced entity currently has `title: "Orders Service"` and `description: "Handles order lifecycle"`
- **THEN** the node's title reads "Orders Service" and its subtitle reads "Handles order lifecycle", regardless of any `title`/`summary` value stored on the step

#### Scenario: Entity-backed node falls back to the entity's name when its title is unresolved

- **WHEN** an entity-backed step's node is rendered and the referenced entity's `title` cannot be resolved (e.g. the reference no longer resolves at all)
- **THEN** the node's title falls back to the entity's raw name parsed from the reference, or to the step's own id if even that is unavailable

#### Scenario: A just-added entity-backed step shows live data before the Flow is saved

- **WHEN** an author picks a reference for a new or just-changed entity-backed step in the current editing session, before saving
- **THEN** the node's card shows that reference's current title/description (resolved for this preview), not a blank subtitle or a raw id

#### Scenario: A just-added entity-backed step's title does not flicker

- **WHEN** an author picks a reference for a new entity-backed step, and the referenced entity's live title differs from a name naively derived from the reference string itself
- **THEN** the node renders the resolved catalog title directly — an author does not see the node briefly show a different, reference-derived guess before it changes to the catalog title

#### Scenario: An entity_ref step with a non-empty title is rejected on save

- **WHEN** a Flow is saved with a step whose `entity_ref` is non-empty and whose `title` is also non-empty
- **THEN** the save is rejected

#### Scenario: An entity_ref step with a non-empty summary is rejected on save

- **WHEN** a Flow is saved with a step whose `entity_ref` is non-empty and whose `summary` is also non-empty
- **THEN** the save is rejected

### Requirement: Endpoint/Operation search lookup for API Call/Event steps

The API Call and Event tiles' lookup SHALL be a single flat search-as-you-type field across every API's Endpoints/Operations, rather than a two-stage "pick an API, then pick within it" flow. Each search result SHALL display the Endpoint/Operation's own identity (method and path, or channel) as its primary text and its owning API's name as secondary text. Selecting a result SHALL store its `query_ref`/`event_ref` on the step, including a snapshot of its display fields at the time of selection. An author SHALL be able to clear the reference, which reverts the node to the plain Step type. The modal SHALL NOT show editable Title or Summary fields for an API Call or Event step (see "API Call/Event steps render title and subtitle from their own snapshot, not typed text" for how the node's title/subtitle are rendered from that snapshot).

The lookup's dropdown SHALL render each match as one shared item row — an icon, the result's primary text, and its owning API's name as secondary text — using the same row shape and the same loading-state treatment as the entity lookup used for Actor/Team/Component/Data/API/System steps (see "Catalog entity lookup for Flow steps"), so an author moving between step kinds within the same modal sees one consistent lookup control rather than a different shape per kind. While a search request is in flight, the lookup SHALL show a loading indicator rather than an abrupt empty-to-populated content change.

When a search term matches more results than fit in one page, the lookup SHALL load further pages of matching results as the author scrolls near the end of the currently-loaded results, appending them to the visible list, rather than stopping at the first page with no way to reach the rest. A loading indicator SHALL be shown at the end of the list for as long as further pages remain available, and SHALL disappear once every matching result has been loaded. Starting a new search (a changed search term) SHALL discard previously loaded pages and begin loading from the first page of the new term's results.

#### Scenario: Search across all APIs' endpoints in one field

- **WHEN** an author types a query into the API Call tile's lookup that matches Endpoints belonging to more than one API
- **THEN** matching Endpoints from every matching API are shown in one flat result list, each showing its method/path and its owning API's name

#### Scenario: Selecting a search result stores the reference and snapshot

- **WHEN** an author selects an Endpoint from the API Call tile's search results
- **THEN** the step's `query_ref` stores that Endpoint's owning API, id, and its current method/path as a snapshot

#### Scenario: Clear an API Call/Event reference

- **WHEN** an author clears a step's API Call or Event lookup
- **THEN** the step's `query_ref`/`event_ref` is removed, and the node reverts to the plain Step type

#### Scenario: Scrolling near the end of loaded results loads the next page

- **WHEN** an author scrolls the lookup's result list near its end, and more matching results exist beyond what is currently loaded
- **THEN** the next page of matching results is fetched and appended to the visible list, and a loading indicator is shown while that page is being fetched

#### Scenario: Reaching the last page ends the scroll-loading behavior

- **WHEN** the most recently loaded page is the last page of matching results for the current search term
- **THEN** no further loading indicator is shown at the end of the list, and further scrolling does not trigger any additional request

#### Scenario: A new search term resets pagination

- **WHEN** an author changes the lookup's search term after one or more additional pages were already loaded for a previous term
- **THEN** the previously loaded pages are discarded and the lookup shows only the new term's first page of results, loading further pages again as the author scrolls

#### Scenario: A search with few results shows no loading indicator at the end

- **WHEN** an author's search query returns fewer matching results than fit in one page
- **THEN** no end-of-list loading indicator is shown, since no further page exists

### Requirement: Stale Endpoint/Operation reference indicator

An API Call or Event node whose resolved Endpoint/Operation currently has `status: removed`, or whose resolved Endpoint currently has `deprecated: true`, SHALL show a warning icon on its card with a tooltip explaining that the reference is stale and naming which condition applies. An Event node whose stored `event_ref.direction`/`event_ref.channel` disagrees with its resolved Operation's current `direction`/`channel_address` SHALL also show this warning icon, with a tooltip comparing the stored value against the current one. An API Call or Event node whose stored `summary` (part of the `query_ref`/`event_ref` snapshot) disagrees with its resolved Endpoint's/Operation's current `summary` SHALL also show this warning icon, with a tooltip comparing the stored summary against the current one — independently of the direction/channel comparison, since either can drift without the other. When any of these conditions co-occur, the tooltip SHALL show all of them, not just one. This indicator SHALL be read-only: it SHALL NOT modify, clear, or remove the step's stored `query_ref`/`event_ref`, and SHALL NOT remove or alter the node itself. A node whose reference cannot be resolved this way (e.g. the APIs plugin is not installed) SHALL render without the indicator rather than erroring. The same warning icon and tooltip SHALL also render for the step being edited inside the step-edit modal (`FlowStepModal`), not only on the canvas card.

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

- **WHEN** an API Call or Event node's reference resolves to an Endpoint/Operation that is `active` and not deprecated, its stored `summary` matches the current one, and (for an Event node) its stored `direction`/`channel` matches the Operation's current values
- **THEN** no warning icon is shown

#### Scenario: Event node warns when its direction/channel has drifted

- **WHEN** an Event node's stored `event_ref.direction`/`event_ref.channel` disagrees with its resolved Operation's current `direction`/`channel_address`, and that Operation is `active` and not deprecated
- **THEN** the node shows a warning icon whose tooltip states the stored direction/channel and the current direction/channel, and its stored `event_ref` is unchanged

#### Scenario: API Call node warns when its Endpoint's summary has drifted

- **WHEN** an API Call node's stored `query_ref.summary` disagrees with its resolved Endpoint's current `summary`, and that Endpoint is `active` and not deprecated
- **THEN** the node shows a warning icon whose tooltip states the stored summary and the current summary, and its stored `query_ref` is unchanged

#### Scenario: Event node warns when its summary has drifted, independent of any direction/channel drift

- **WHEN** an Event node's stored `event_ref.summary` disagrees with its resolved Operation's current `summary`, while `event_ref.direction`/`event_ref.channel` still match that Operation's current `direction`/`channel_address`
- **THEN** the node shows a warning icon whose tooltip states the summary drift, with no direction/channel drift line, and its stored `event_ref` is unchanged

#### Scenario: No summary-drift warning when the stored summary matches

- **WHEN** an API Call or Event node's stored `summary` matches its resolved Endpoint's/Operation's current `summary` exactly (including when both are blank)
- **THEN** no warning icon is shown for that reason (other conditions from this requirement may still apply independently)

#### Scenario: Tooltip shows every applicable condition when more than one applies

- **WHEN** an Event node's resolved Operation currently has `status: removed`, its stored `event_ref.direction`/`event_ref.channel` also disagrees with that Operation's last-known `direction`/`channel_address`, and its stored `summary` also disagrees with the Operation's last-known `summary`
- **THEN** the tooltip states all three conditions, rather than showing only one

#### Scenario: The stale-reference warning also renders inside the step-edit modal

- **WHEN** an author opens the step-edit modal for a step whose node currently shows a stale-reference warning icon
- **THEN** the same warning icon and tooltip are shown inside the modal, next to the field the warning concerns

### Requirement: Refresh action pulls live values into a stale step's ref

Wherever the stale-reference warning icon from the "Stale Endpoint/Operation reference indicator" requirement is shown for an Event node with a direction/channel or summary drift, or for an API Call node with a summary drift, a refresh control SHALL also be shown next to it — on the canvas card, and inside the step-edit modal when that step happens to be open there. Activating the control on the canvas card SHALL apply the current live values (`direction`/`channel` and/or `summary` for an Event step; `summary` only for an API Call step, since its `method`/`path` cannot drift by construction) directly onto that step's `event_ref`/`query_ref`, without opening the edit modal — the same way deleting a step or reconnecting a transition already applies immediately, undone only by not saving the whole Flow. Activating the control inside the step-edit modal SHALL instead populate the modal's own in-memory Operation/Endpoint form state with the current live values, without persisting anything; the step's stored `event_ref`/`query_ref` SHALL remain unchanged unless and until the author explicitly saves the step from the modal, and closing or cancelling the modal after activating it SHALL leave the step's stored data unchanged. Opening the step-edit modal by clicking the node itself (not its refresh control) SHALL NOT populate this field from live values — the modal's inputs SHALL initialize from the step's stored data exactly as before this control existed.

#### Scenario: Refresh control appears next to an Event node's drift warning

- **WHEN** an Event node shows the direction/channel drift warning, the summary-drift warning, or both
- **THEN** a refresh control is shown next to the warning icon, both on the canvas card and inside the step-edit modal

#### Scenario: Refresh control appears next to an API Call node's summary-drift warning

- **WHEN** an API Call node shows the summary-drift warning
- **THEN** a refresh control is shown next to the warning icon, both on the canvas card and inside the step-edit modal

#### Scenario: No refresh control on an API Call node for a removed/deprecated-only warning

- **WHEN** an API Call node's resolved Endpoint is `removed` or `deprecated`, but its stored `summary` still matches the Endpoint's current `summary`
- **THEN** no refresh control is shown next to its warning icon, since nothing on the `query_ref` has actually drifted

#### Scenario: Activating the canvas card's refresh control applies the change directly, without opening the modal

- **WHEN** an author activates the refresh control on an Event node's canvas card, whose stored `event_ref` is `{direction: "send", channel: "orders.created"}` and whose resolved Operation is currently `receive`/`orders.events`
- **THEN** the step's `event_ref` is updated to `{direction: "receive", channel: "orders.events"}` immediately, the step-edit modal is not opened, and the change is undone only by not saving the Flow (or by reversing it, e.g. via another edit)

#### Scenario: Activating the canvas card's refresh control on an API Call node updates only its summary

- **WHEN** an author activates the refresh control on an API Call node's canvas card, whose stored `query_ref.summary` is `"List orders"` and whose resolved Endpoint's current `summary` is `"List all orders"`
- **THEN** the step's `query_ref.summary` is updated to `"List all orders"` immediately, with `method`/`path`/`endpoint`/`api` unchanged, and the step-edit modal is not opened

#### Scenario: Activating the refresh control inside the step-edit modal populates the form without saving

- **WHEN** an author opens the step-edit modal for a stale step by clicking the node directly, then activates the refresh control shown inside the modal
- **THEN** the modal's Operation/Endpoint field reflects the current live values, and the step's stored `event_ref`/`query_ref` remains exactly as it was before, until the author clicks the modal's Save

#### Scenario: Cancelling the modal after an in-modal refresh leaves the stored step unchanged

- **WHEN** an author activates the refresh control inside the step-edit modal, then closes the modal without clicking Save
- **THEN** the step's stored data is exactly as it was before the refresh control was activated

#### Scenario: Opening a step normally never prefills live values

- **WHEN** an author opens the step-edit modal for a step with an active stale-reference warning by clicking the node directly, not a refresh control
- **THEN** the modal's inputs are populated from the step's stored data only, with no live values applied

### Requirement: Visual editor structural feedback

The Visual editor SHALL report invalid step IDs and invalid transitions before save, and SHALL enforce structural rules at the moment an author attempts them on the canvas. It SHALL not allow a drag-to-connect gesture to complete a transition to an unknown step or a transition that introduces a cycle — the attempted connection SHALL be rejected with an inline explanation instead of being added. A drag-to-connect gesture to a step that already has one or more incoming transitions SHALL be allowed, adding another incoming connection to that step. The editor SHALL block saving while any validation error is present. A step's `id` is not an editable field anywhere in the node-type picker or edit modal (see "Step id is not a visual-editor field"); a duplicate id, or any other structural error, can therefore only be introduced by hand-editing the JSON rail, where it is caught live by the "Synchronized Visual and JSON modes" requirement's structural-validity gate rather than surfacing only at save.

#### Scenario: Reconverging a connection is allowed

- **WHEN** an author drags a connection from one node to a step that is already targeted by another step's transition
- **THEN** the Visual editor adds the connection, and the target step's node shows an incoming connection from each source step

#### Scenario: A structurally invalid Flow cannot be saved

- **WHEN** an author attempts to save a Flow whose steps (however produced) fail structural validation — for example, two steps sharing the same id
- **THEN** the save is blocked with an inline explanation of the error, as a backstop independent of how the invalid state was reached

### Requirement: Synchronized Visual and JSON modes

The Flow edit page SHALL always show the interactive canvas as its primary, full-width view, and SHALL provide a control that opens or collapses a JSON rail panel alongside it. The JSON rail SHALL be collapsed by default when the Flow edit page loads. The canvas and the JSON rail SHALL represent the same in-memory steps data. Editing on the canvas SHALL update the JSON rail's content, when open, without requiring a save. Typing in the JSON rail SHALL update the canvas only when the JSON both parses and satisfies the supported step schema, AND the resulting steps pass structural validation (unique step ids, every transition target resolves to an existing step, no cycle) — evaluated against the freshly-typed candidate, not the canvas's already-committed state. While the JSON fails either check, the canvas SHALL keep showing its last successfully-parsed-and-valid state, and the JSON rail SHALL show the specific validation issue inline without discarding the entered text. Steps that reach the canvas without a stored `position` SHALL be placed by autolayout rather than left unplaced.

#### Scenario: JSON rail is collapsed when the Flow edit page loads

- **WHEN** an author opens the Flow edit page
- **THEN** the JSON rail is not shown by default, and the canvas occupies the full-width primary view until the author explicitly opens the rail

#### Scenario: Canvas edits reflect in the open JSON rail

- **WHEN** an author edits a step title or transition on the canvas while the JSON rail is open
- **THEN** the JSON rail displays those edits in the serialized `steps` array without requiring a save

#### Scenario: Invalid JSON does not affect the canvas

- **WHEN** an author types JSON in the rail that is malformed or fails schema validation
- **THEN** the canvas keeps showing its last valid state, and the JSON rail shows the validation issue and retains the entered text

#### Scenario: A structurally-broken JSON edit does not reach the canvas

- **WHEN** an author edits a step's `id` in the JSON rail without updating another step's `next_step`/`next_steps` that targeted the old id, so the edited JSON parses and satisfies the step schema but now transitions to an unknown step id
- **THEN** the canvas keeps showing its last valid state — it does not render the dangling transition — and the JSON rail shows the structural error inline, retaining the entered text

#### Scenario: A reconverging JSON edit reaches the canvas

- **WHEN** an author edits the JSON rail so that two different steps each transition to the same target step id, and the edit otherwise parses and satisfies the step schema
- **THEN** the canvas updates to show the target step with an incoming connection from each of those steps, without any structural error

#### Scenario: Steps without a stored position autolayout on the canvas

- **WHEN** the canvas renders a set of steps and one or more have no `position`
- **THEN** those steps are placed on the canvas by autolayout instead of stacking at a default coordinate

### Requirement: Step id is not a visual-editor field

A step's `id` SHALL NOT be shown or editable anywhere in the node-type picker or edit modal, for any step kind. A new step SHALL be assigned a fresh, non-colliding id automatically. An author who wants to set or change a specific step's id SHALL do so by editing the JSON rail directly.

#### Scenario: Adding a step never asks for an id

- **WHEN** an author adds a new step of any kind through the node-type picker
- **THEN** the step is created with an automatically-assigned id, and the picker/modal never prompts for or displays an id field

#### Scenario: Editing an existing step's modal does not offer to change its id

- **WHEN** an author opens the edit modal for an existing step
- **THEN** no id field is shown or editable in the modal, regardless of the step's kind

#### Scenario: An author changes a step's id via the JSON rail

- **WHEN** an author edits a step's `id` directly in the JSON rail, along with every `next_step`/`next_steps` reference that targeted the old id
- **THEN** the change is accepted and reflected on the canvas once the edit is both shape-valid and structurally valid

### Requirement: API Call/Event steps render title and subtitle from their own snapshot, not typed text

The edit modal SHALL NOT show editable Title or Summary fields for an API Call or Event step. An API Call node's card SHALL always render its `query_ref` snapshot's `method` and `path` as its title, and the picked Endpoint's own `summary` (captured into the `query_ref` snapshot at pick time, falling back to the owning API's raw name when that summary is blank) as its subtitle. An Event node's card SHALL always render its `event_ref` snapshot's `channel` and `direction` as its title, and the picked Operation's own `summary` (captured into the `event_ref` snapshot at pick time, falling back to the owning API's raw name when that summary is blank) as its subtitle. None of this is fetched live — all of it is derived from the step's own already-stored `query_ref`/`event_ref`, preserving the offline-canvas-render invariant those snapshots exist for. A step carrying a non-empty `query_ref` or `event_ref` together with a non-empty `title` or `summary` SHALL be rejected on save.

#### Scenario: Selecting an Endpoint or Operation does not offer Title/Summary fields to edit

- **WHEN** an author picks an Endpoint for an API Call step, or an Operation for an Event step
- **THEN** no Title or Summary input is shown for that step; the modal offers no way to type custom text for it

#### Scenario: API Call node renders its method and path, and the picked Endpoint's own summary

- **WHEN** an API Call step's node is rendered, and its `query_ref` snapshot has `method: "POST"`, `path: "/orders"`, `api: "api:orders-api"`, and `summary: "Create an order"`
- **THEN** the node's title reads "POST /orders" and its subtitle reads "Create an order", regardless of any `title`/`summary` value stored on the step itself

#### Scenario: API Call node falls back to the owning API's name when the picked Endpoint has no summary

- **WHEN** an API Call step's node is rendered, and its `query_ref` snapshot has `api: "api:orders-api"` and no non-empty `summary`
- **THEN** the node's subtitle reads "orders-api"

#### Scenario: Event node renders its channel and direction, and the picked Operation's own summary

- **WHEN** an Event step's node is rendered, and its `event_ref` snapshot has `channel: "orders.created"`, `direction: "send"`, `api: "api:orders-api"`, and `summary: "Emitted when an order is created"`
- **THEN** the node's title reads "orders.created (send)" and its subtitle reads "Emitted when an order is created", regardless of any `title`/`summary` value stored on the step itself

#### Scenario: Event node falls back to the owning API's name when the picked Operation has no summary

- **WHEN** an Event step's node is rendered, and its `event_ref` snapshot has `api: "api:orders-api"` and no non-empty `summary`
- **THEN** the node's subtitle reads "orders-api"

#### Scenario: A query_ref step with a non-empty title is rejected on save

- **WHEN** a Flow is saved with a step whose `query_ref` is non-empty and whose `title` is also non-empty
- **THEN** the save is rejected

#### Scenario: An event_ref step with a non-empty summary is rejected on save

- **WHEN** a Flow is saved with a step whose `event_ref` is non-empty and whose `summary` is also non-empty
- **THEN** the save is rejected

### Requirement: Node-type picker tile colors and layout

The node-type picker's System tile SHALL use the same fixed identity color as System's canvas node, distinct from API's color. The node-type picker's Component tile color SHALL NOT be presented as representative of any specific Component subtype's actual canvas color, since a resolved Component's canvas color is always derived from its real subtype rather than a single generic color. The picker's grid arrangement SHALL NOT place two tiles carrying the same identity color adjacent to each other, horizontally or vertically. The picker's grid SHALL hold twelve tiles arranged as a two-column grid with no partial trailing row.

#### Scenario: System's picker tile and canvas node share one color, distinct from API

- **WHEN** the node-type picker is shown, and separately a System node is rendered on the canvas
- **THEN** both render in the same fixed color, and that color differs from API's fixed color

#### Scenario: No two adjacent picker tiles share a color

- **WHEN** the node-type picker's grid is rendered
- **THEN** for every pair of tiles that are horizontally or vertically adjacent, their identity colors differ

#### Scenario: The picker grid has no partial trailing row

- **WHEN** the node-type picker's grid is rendered with Flow and Link included alongside the ten existing tiles
- **THEN** the grid renders as six full rows of two tiles each, with no row containing only one tile

### Requirement: Flow reference lookup for Flow steps

The node-type picker and edit modal SHALL provide a searchable lookup for a step's `flow_ref`, searching by Flow name across existing Flows. The lookup SHALL store the selected Flow's id. An author SHALL be able to clear the reference, which reverts the node to the plain Step type. For a Flow-backed step, the modal SHALL NOT show editable Title or Summary fields — the node's card SHALL always render the referenced Flow's current `name` as its title and its current `description` as its subtitle, resolved live and never taken from any value stored on the step itself. A step carrying a non-empty `flow_ref` together with a non-empty `title` or `summary` SHALL be rejected on save. The lookup MAY include the Flow currently being edited among its results; selecting it is not an error.

#### Scenario: Select a Flow reference

- **WHEN** an author selects the Flow type and searches for and selects a Flow in its search lookup
- **THEN** the step stores that Flow's id as `flow_ref`, and the node renders styled as a Flow node

#### Scenario: Clear a Flow reference

- **WHEN** an author clears a step's Flow lookup
- **THEN** the step's `flow_ref` is removed, and the node reverts to the plain Step type

#### Scenario: Selecting a Flow does not offer Title/Summary fields to edit

- **WHEN** an author selects a reference for a Flow-backed step in the node-type picker or edit modal
- **THEN** no Title or Summary input is shown for that step; the modal offers no way to type custom text for it

#### Scenario: Flow-backed node renders the referenced Flow's live name and description

- **WHEN** a Flow-backed step's node is rendered, and the referenced Flow currently has `name: "Checkout"` and `description: "Cart to payment"`
- **THEN** the node's title reads "Checkout" and its subtitle reads "Cart to payment", regardless of any `title`/`summary` value stored on the step

### Requirement: Read-only navigate action for Flow and Link nodes

A Flow node's or Link node's card SHALL render a small navigate control, visually distinct from its identity chip, using an outbound-link icon. Activating it SHALL open the node's target — the referenced Flow's detail page for a Flow node, or the `link_url` for a Link node — in a new browser tab, leaving the current Flow's view unchanged. This control SHALL render only on the read-only detail page's canvas; the edit page's canvas SHALL NOT render it — clicking a Flow or Link node there opens its edit modal like any other node. Pressing down on a Flow or Link node's card and dragging, without activating the navigate control itself, SHALL pan the canvas as it would from any other node's card, and SHALL NOT trigger navigation. A Flow node whose `flow_ref` does not currently resolve to an existing Flow SHALL NOT render an active navigate control.

#### Scenario: Activating a Flow node's navigate control opens its target in a new tab

- **WHEN** a user activates a Flow node's navigate control on the read-only detail page
- **THEN** the referenced Flow's detail page opens in a new browser tab, and the current tab's view is unchanged

#### Scenario: Activating a Link node's navigate control opens its URL in a new tab

- **WHEN** a user activates a Link node's navigate control on the read-only detail page
- **THEN** the node's `link_url` opens in a new browser tab, and the current tab's view is unchanged

#### Scenario: The navigate control is absent on the edit page's canvas

- **WHEN** an author views a Flow or Link node on the edit page's canvas
- **THEN** no navigate control is rendered on its card

#### Scenario: Panning the canvas from a Flow or Link node does not navigate

- **WHEN** a user presses down on a Flow or Link node's card, away from the navigate control, and drags to pan the read-only canvas
- **THEN** the canvas viewport pans, and no navigation occurs

#### Scenario: A Flow node with an unresolved target has no active navigate control

- **WHEN** a Flow node's `flow_ref` does not currently resolve to an existing Flow
- **THEN** its navigate control is not rendered, or is rendered disabled

### Requirement: Stale Flow reference indicator

A Flow node whose `flow_ref` no longer resolves to an existing Flow SHALL show a warning icon on its card with a tooltip explaining that the referenced Flow no longer exists. This indicator SHALL be read-only: it SHALL NOT modify, clear, or remove the step's stored `flow_ref`, and SHALL NOT remove or alter the node itself. The same warning icon and tooltip SHALL also render for the step being edited inside the step-edit modal, not only on the canvas card.

#### Scenario: Flow node warns when its target no longer resolves

- **WHEN** a Flow node's `flow_ref` no longer resolves to an existing Flow (e.g. it was deleted)
- **THEN** the node shows a visible warning icon with a tooltip explaining the referenced Flow no longer exists

#### Scenario: Flow node with a resolving target shows no warning

- **WHEN** a Flow node's `flow_ref` resolves to an existing Flow
- **THEN** no warning icon is shown on that node

#### Scenario: The stale-reference indicator does not modify the stored flow_ref

- **WHEN** a Flow node's stale-reference warning icon is shown
- **THEN** the step's stored `flow_ref` remains unchanged, and the node itself is not removed from the canvas
