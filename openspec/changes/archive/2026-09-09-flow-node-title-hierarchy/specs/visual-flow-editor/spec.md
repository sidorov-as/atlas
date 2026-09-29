## MODIFIED Requirements

### Requirement: Catalog entity lookup for Flow steps

The node-type picker and edit modal SHALL provide a searchable catalog lookup for a step's `entity_ref`, scoped to the kind matching the selected node type (Actor → User, Team → Group, Component → Component, Data → Resource, API → API, System → System). The lookup SHALL store the selected entity's canonical `kind:name` reference. An author SHALL be able to clear the reference, which reverts the node to the plain Step type. When a reference is selected or changed, the modal SHALL prefill the step's Title field with the entity's name and its Summary field with the entity's description, but only into a field that is currently empty — an already-populated Title or Summary SHALL never be overwritten, whether by prefill on a fresh selection or by changing to a different reference. The node's card SHALL show the step's Summary as its subtitle once Summary is non-empty; while Summary remains empty, the card's subtitle SHALL show the referenced entity's name, as it does when no Summary is set.

#### Scenario: Select a component reference

- **WHEN** an author selects the Component type and searches for and selects a Component in its entity lookup
- **THEN** the step stores that Component's canonical `component:name` reference, and the node renders styled as a Component, using that Component's actual subtype icon and color

#### Scenario: Clear a reference

- **WHEN** an author clears a step's entity lookup
- **THEN** the step's `entity_ref` is removed, and the node reverts to the plain Step type

#### Scenario: Selecting a reference prefills empty Title/Summary

- **WHEN** an author selects a Component for a step whose Title and Summary are both currently empty
- **THEN** the Title field is filled with that Component's name and the Summary field with that Component's description, both remaining freely editable afterward

#### Scenario: Prefill never overwrites existing text

- **WHEN** an author has already typed a Title for a step, then selects (or changes to a different) Component reference
- **THEN** the Title field's existing text is left unchanged

#### Scenario: Card subtitle shows the filled Summary

- **WHEN** a step's `entity_ref` resolves to a Component and the step's Summary is non-empty
- **THEN** the node's subtitle shows that Summary text, not the Component's reference

#### Scenario: Card subtitle falls back to the entity's name when Summary is empty

- **WHEN** a step's `entity_ref` resolves to a Component and the step's Summary is empty
- **THEN** the node's subtitle shows that Component's name, exactly as it renders when no Summary is set

### Requirement: Endpoint/Operation search lookup for API Call/Event steps

The API Call and Event tiles' lookup SHALL be a single flat search-as-you-type field across every API's Endpoints/Operations, rather than a two-stage "pick an API, then pick within it" flow. Each search result SHALL display the Endpoint/Operation's own identity (method and path, or channel) as its primary text and its owning API's name as secondary text. Selecting a result SHALL store its `query_ref`/`event_ref` on the step, including a snapshot of its display fields at the time of selection. An author SHALL be able to clear the reference, which reverts the node to the plain Step type. When a result is selected or changed, the modal SHALL prefill the step's Title field with the selected Endpoint/Operation's method+path (API Call) or channel+direction (Event), and its Summary field with that Endpoint/Operation's own summary, but only into a field that is currently empty — an already-populated Title or Summary SHALL never be overwritten. The node's card SHALL show the step's Summary as its subtitle once Summary is non-empty; while Summary remains empty, the card's subtitle SHALL show the owning API's name.

#### Scenario: Search across all APIs' endpoints in one field

- **WHEN** an author types a query into the API Call tile's lookup that matches Endpoints belonging to more than one API
- **THEN** matching Endpoints from every matching API are shown in one flat result list, each showing its method/path and its owning API's name

#### Scenario: Selecting a search result stores the reference and snapshot

- **WHEN** an author selects an Endpoint from the API Call tile's search results
- **THEN** the step's `query_ref` stores that Endpoint's owning API, id, and its current method/path as a snapshot

#### Scenario: Clear an API Call/Event reference

- **WHEN** an author clears a step's API Call or Event lookup
- **THEN** the step's `query_ref`/`event_ref` is removed, and the node reverts to the plain Step type

#### Scenario: Selecting an Endpoint prefills empty Title/Summary

- **WHEN** an author selects an Endpoint `POST /bookings/{id}/cancel` for a step whose Title and Summary are both currently empty
- **THEN** the Title field is filled with "POST /bookings/{id}/cancel" and the Summary field with that Endpoint's own summary, both remaining freely editable afterward

#### Scenario: Selecting an Operation prefills empty Title/Summary

- **WHEN** an author selects an Operation on channel `orders.created` with `send` direction for a step whose Title and Summary are both currently empty
- **THEN** the Title field is filled with "orders.created (send)" and the Summary field with that Operation's own summary, both remaining freely editable afterward

#### Scenario: Prefill never overwrites an existing API Call/Event Title or Summary

- **WHEN** an author has already typed a Summary for a step, then selects a different Endpoint for it
- **THEN** the Summary field's existing text is left unchanged

#### Scenario: API Call/Event card subtitle shows the filled Summary

- **WHEN** a step carries a `query_ref` or `event_ref` and the step's Summary is non-empty
- **THEN** the node's subtitle shows that Summary text, not the endpoint/operation's method+path/channel+direction or the owning API's name

#### Scenario: API Call/Event card subtitle falls back to the owning API's name when Summary is empty

- **WHEN** a step carries a `query_ref` or `event_ref` and the step's Summary is empty
- **THEN** the node's subtitle shows the owning API's name
