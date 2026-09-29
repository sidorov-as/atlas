## MODIFIED Requirements

### Requirement: Stale Endpoint/Operation reference indicator

An API Call or Event node whose resolved Endpoint/Operation currently has `status: removed`, or whose resolved Endpoint currently has `deprecated: true`, SHALL show a warning icon on its card with a tooltip explaining that the reference is stale and naming which condition applies. An Event node whose stored `event_ref.direction`/`event_ref.channel` disagrees with its resolved Operation's current `direction`/`channel_address` SHALL also show this warning icon, with a tooltip comparing the stored value against the current one; when this drift co-occurs with a removed/deprecated condition, the tooltip SHALL show both, not just one. This indicator SHALL be read-only: it SHALL NOT modify, clear, or remove the step's stored `query_ref`/`event_ref`, and SHALL NOT remove or alter the node itself. A node whose reference cannot be resolved this way (e.g. the APIs plugin is not installed) SHALL render without the indicator rather than erroring. The same warning icon and tooltip SHALL also render for the step being edited inside the step-edit modal (`FlowStepModal`), not only on the canvas card.

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

- **WHEN** an API Call or Event node's reference resolves to an Endpoint/Operation that is `active` and not deprecated, and (for an Event node) its stored `direction`/`channel` matches the Operation's current values
- **THEN** no warning icon is shown

#### Scenario: Event node warns when its direction/channel has drifted

- **WHEN** an Event node's stored `event_ref.direction`/`event_ref.channel` disagrees with its resolved Operation's current `direction`/`channel_address`, and that Operation is `active` and not deprecated
- **THEN** the node shows a warning icon whose tooltip states the stored direction/channel and the current direction/channel, and its stored `event_ref` is unchanged

#### Scenario: Tooltip shows both removed and drift conditions when both apply

- **WHEN** an Event node's resolved Operation currently has `status: removed`, and its stored `event_ref.direction`/`event_ref.channel` also disagrees with that Operation's last-known `direction`/`channel_address`
- **THEN** the tooltip states both the removed condition and the direction/channel drift, rather than showing only one

#### Scenario: The stale-reference warning also renders inside the step-edit modal

- **WHEN** an author opens the step-edit modal for a step whose node currently shows a stale-reference warning icon
- **THEN** the same warning icon and tooltip are shown inside the modal, next to the field the warning concerns

## ADDED Requirements

### Requirement: Refresh action pulls live values into a stale step's edit inputs

Wherever the stale-reference warning icon from the "Stale Endpoint/Operation reference indicator" requirement is shown for an Event node with a direction/channel drift — on a canvas node card, or inside the step-edit modal — a refresh control SHALL also be shown next to it. Activating this control SHALL open the step-edit modal for that step (if not already open) and populate its Operation selection (and its derived `direction`/`channel`) with the current live values, without persisting anything. The step's stored `event_ref` SHALL remain unchanged unless and until the author explicitly saves the step from the modal; closing or cancelling the modal after activating the refresh control SHALL leave the step's stored data unchanged. Opening the step-edit modal by any means other than this control SHALL NOT populate this field from live values — the modal's inputs SHALL initialize from the step's stored data exactly as before this control existed. An API Call node SHALL NOT show this control.

#### Scenario: Refresh control appears next to an Event node's drift warning

- **WHEN** an Event node shows the direction/channel drift warning
- **THEN** a refresh control is shown next to the warning icon, both on the canvas card and inside the step-edit modal

#### Scenario: Activating refresh on an Event step populates the modal without saving

- **WHEN** an author activates the refresh control for an Event step whose stored `event_ref` is `{direction: "send", channel: "orders.created"}` and whose resolved Operation is currently `receive`/`orders.events`
- **THEN** the step-edit modal opens (or updates, if already open) showing the Operation field reflecting `receive`/`orders.events`, and the step's stored `event_ref` remains `{direction: "send", channel: "orders.created"}` until the author saves

#### Scenario: Cancelling after refresh leaves the stored step unchanged

- **WHEN** an author activates the refresh control for a step, then closes the step-edit modal without clicking Save
- **THEN** the step's stored data is exactly as it was before the refresh control was activated

#### Scenario: Opening a step normally never prefills live values

- **WHEN** an author opens the step-edit modal for a step with an active stale-reference warning by clicking the node directly, not the refresh control
- **THEN** the modal's inputs are populated from the step's stored data only, with no live values applied

#### Scenario: No refresh control on an API Call node

- **WHEN** an API Call node's resolved Endpoint is `removed` or `deprecated`
- **THEN** no refresh control is shown next to its warning icon, since a `query_ref`'s `method`/`path` cannot drift
