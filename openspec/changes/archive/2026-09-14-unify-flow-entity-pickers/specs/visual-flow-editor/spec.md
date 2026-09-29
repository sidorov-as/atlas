## MODIFIED Requirements

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
