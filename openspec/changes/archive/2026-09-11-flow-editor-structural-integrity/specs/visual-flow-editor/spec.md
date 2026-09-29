## MODIFIED Requirements

### Requirement: Catalog entity lookup for Flow steps

The node-type picker and edit modal SHALL provide a searchable catalog lookup for a step's `entity_ref`, scoped to the kind matching the selected node type (Actor → User, Team → Group, Component → Component, Data → Resource, API → API, System → System). The lookup SHALL store the selected entity's canonical `kind:name` reference. An author SHALL be able to clear the reference, which reverts the node to the plain Step type. For an entity-backed step, the modal SHALL NOT show editable Title or Summary fields — the node's card SHALL always render the referenced entity's current `title` as its title (falling back to the entity's raw name, then to the step's own id, when the resolved title is unavailable) and the entity's current `description` as its subtitle, resolved live and never taken from any value stored on the step itself. A step carrying a non-empty `entity_ref` together with a non-empty `title` or `summary` SHALL be rejected on save.

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

#### Scenario: An entity_ref step with a non-empty title is rejected on save

- **WHEN** a Flow is saved with a step whose `entity_ref` is non-empty and whose `title` is also non-empty
- **THEN** the save is rejected

#### Scenario: An entity_ref step with a non-empty summary is rejected on save

- **WHEN** a Flow is saved with a step whose `entity_ref` is non-empty and whose `summary` is also non-empty
- **THEN** the save is rejected

### Requirement: Visual editor structural feedback

The Visual editor SHALL report invalid step IDs and invalid transitions before save, and SHALL enforce structural rules at the moment an author attempts them on the canvas. It SHALL not allow a drag-to-connect gesture to complete a transition to an unknown step, a transition that gives a target more than one incoming edge, or a transition that introduces a cycle — the attempted connection SHALL be rejected with an inline explanation instead of being added. The editor SHALL block saving while any validation error is present. A step's `id` is not an editable field anywhere in the node-type picker or edit modal (see "Step id is not a visual-editor field"); a duplicate id, or any other structural error, can therefore only be introduced by hand-editing the JSON rail, where it is caught live by the "Synchronized Visual and JSON modes" requirement's structural-validity gate rather than surfacing only at save.

#### Scenario: Attempt to reconverge branches

- **WHEN** an author drags a connection from one node to a step that is already targeted by another step's transition
- **THEN** the Visual editor rejects the connection and explains that Flow branches cannot reconverge

#### Scenario: A structurally invalid Flow cannot be saved

- **WHEN** an author attempts to save a Flow whose steps (however produced) fail structural validation — for example, two steps sharing the same id
- **THEN** the save is blocked with an inline explanation of the error, as a backstop independent of how the invalid state was reached

### Requirement: Synchronized Visual and JSON modes

The Flow edit page SHALL always show the interactive canvas as its primary, full-width view, and SHALL provide a control that opens or collapses a JSON rail panel alongside it. The JSON rail SHALL be collapsed by default when the Flow edit page loads. The canvas and the JSON rail SHALL represent the same in-memory steps data. Editing on the canvas SHALL update the JSON rail's content, when open, without requiring a save. Typing in the JSON rail SHALL update the canvas only when the JSON both parses and satisfies the supported step schema, AND the resulting steps pass structural validation (unique step ids, every transition target resolves to an existing step, no target with more than one incoming transition, no cycle) — evaluated against the freshly-typed candidate, not the canvas's already-committed state. While the JSON fails either check, the canvas SHALL keep showing its last successfully-parsed-and-valid state, and the JSON rail SHALL show the specific validation issue inline without discarding the entered text. Steps that reach the canvas without a stored `position` SHALL be placed by autolayout rather than left unplaced.

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

#### Scenario: Steps without a stored position autolayout on the canvas

- **WHEN** the canvas renders a set of steps and one or more have no `position`
- **THEN** those steps are placed on the canvas by autolayout instead of stacking at a default coordinate

### Requirement: Stale Endpoint/Operation reference indicator

An API Call or Event node whose resolved Endpoint/Operation currently has `status: removed`, or whose resolved Endpoint currently has `deprecated: true`, SHALL show a warning icon on its card with a tooltip explaining that the reference is stale and naming which condition applies. An Event node whose stored `event_ref.direction`/`event_ref.channel` disagrees with its resolved Operation's current `direction`/`channel_address` SHALL also show this warning icon, with a tooltip comparing the stored value against the current one. An API Call or Event node whose stored `summary` (part of the `query_ref`/`event_ref` snapshot, flow-editor-structural-integrity design.md Decision 7's second addendum) disagrees with its resolved Endpoint's/Operation's current `summary` SHALL also show this warning icon, with a tooltip comparing the stored summary against the current one — independently of the direction/channel comparison, since either can drift without the other. When any of these conditions co-occur, the tooltip SHALL show all of them, not just one. This indicator SHALL be read-only: it SHALL NOT modify, clear, or remove the step's stored `query_ref`/`event_ref`, and SHALL NOT remove or alter the node itself. A node whose reference cannot be resolved this way (e.g. the APIs plugin is not installed) SHALL render without the indicator rather than erroring. The same warning icon and tooltip SHALL also render for the step being edited inside the step-edit modal (`FlowStepModal`), not only on the canvas card.

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

## ADDED Requirements

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

The node-type picker's System tile SHALL use the same fixed identity color as System's canvas node, distinct from API's color. The node-type picker's Component tile color SHALL NOT be presented as representative of any specific Component subtype's actual canvas color, since a resolved Component's canvas color is always derived from its real subtype rather than a single generic color. The picker's grid arrangement SHALL NOT place two tiles carrying the same identity color adjacent to each other, horizontally or vertically.

#### Scenario: System's picker tile and canvas node share one color, distinct from API

- **WHEN** the node-type picker is shown, and separately a System node is rendered on the canvas
- **THEN** both render in the same fixed color, and that color differs from API's fixed color

#### Scenario: No two adjacent picker tiles share a color

- **WHEN** the node-type picker's grid is rendered
- **THEN** for every pair of tiles that are horizontally or vertically adjacent, their identity colors differ
