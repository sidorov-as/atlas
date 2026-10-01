## ADDED Requirements

### Requirement: Flow skill builds a flow through dialogue
`atlas-flow` SHALL guide the user from a description of a process to a complete flow by asking, one question at a time, for the process's purpose, its home system, its steps in order, and where the path branches or rejoins. It SHALL propose a name and description itself.

#### Scenario: Home system is established first
- **WHEN** a user starts describing a process
- **THEN** the skill establishes which existing system the flow belongs to, offering matches from the catalog, before drafting steps

#### Scenario: Branching is captured
- **WHEN** the user describes a point where the process can go more than one way
- **THEN** the skill models it as a step with several labeled transitions and, where paths rejoin, as several steps leading to the same step

### Requirement: Flow steps are bound to catalog resources where they exist
For each step, `atlas-flow` SHALL search the catalog and bind the step to an existing entity when one matches, to a specific API endpoint or operation when the step is a call or a message, and otherwise to an external participant or a plain step. It SHALL NOT bind a step to an entity it has not confirmed exists, and SHALL give each step at most one reference: an entity, an endpoint, an operation, an external label, a nested flow, or a link. It SHALL use the step field names and styling fields the flow tool schema defines, including snake_case field names and `color` rather than the deprecated `label_theme`.

#### Scenario: Step bound to an entity
- **WHEN** a step corresponds to an existing component
- **THEN** the step references that component

#### Scenario: Step bound to an endpoint
- **WHEN** a step is a call to a documented HTTP endpoint
- **THEN** the step references that endpoint of its API

#### Scenario: Unknown participant becomes external
- **WHEN** a step involves a party that is not in the catalog
- **THEN** the step is recorded as an external participant, and the skill offers to document the missing entity afterward

### Requirement: Flow skill binds external steps after the missing entities are documented
When a flow contains external steps standing in for entities missing from the catalog, `atlas-flow` SHALL list those steps in its summary before saving, and after saving SHALL offer to document the missing entities through `atlas-curator`. Once the entities exist, it SHALL read the flow, replace the external label of each corresponding step with an entity reference, and save the complete merged step list, changing no other step.

#### Scenario: Unbound steps are listed before saving
- **WHEN** the flow summary is shown and some steps are external because their entity is missing
- **THEN** the summary names those steps and the entities they could be bound to

#### Scenario: Offer after saving
- **WHEN** a flow containing such steps has been saved
- **THEN** the skill offers to document the missing entities through `atlas-curator`

#### Scenario: Steps are bound once the entity exists
- **WHEN** a previously missing entity has been created
- **THEN** the skill replaces that step's external label with a reference to the entity and leaves every other step unchanged

### Requirement: Flow skill validates before saving and shows a summary
`atlas-flow` SHALL check step ids for uniqueness, that every transition targets an existing step, that transitions contain no cycle, and the size limits, and SHALL use the server's validation tool when available. It SHALL show the user the flow's steps and links as a summary and SHALL save only after the user confirms.

#### Scenario: Cycle is caught before saving
- **WHEN** the drafted transitions form a cycle
- **THEN** the skill reports the steps involved and revises the flow with the user before saving

#### Scenario: Summary precedes the write
- **WHEN** the flow is ready
- **THEN** the skill shows its steps and links and waits for confirmation before creating it

### Requirement: Flow skill picks real icons and updates safely
`atlas-flow` SHALL choose a step icon only from names returned by the icon search tool, and SHALL omit the icon when none fits. When changing an existing flow, it SHALL read the current flow first and send the full merged step list, because an update replaces the steps.

#### Scenario: Icon comes from the search tool
- **WHEN** the skill sets a step icon
- **THEN** the name was returned by the icon search tool

#### Scenario: Existing flow is edited without losing steps
- **WHEN** the user adds a step to an existing flow
- **THEN** the skill reads the flow, adds the step to the existing list, and saves the complete list

### Requirement: Flow skill requires the flows tools
`atlas-flow` SHALL stop with an explanation when the flow tools are not available, and SHALL report that flow writes need the `flows:write` scope when they are rejected for that reason.

#### Scenario: Flows plugin absent
- **WHEN** the connected server offers no flow tools
- **THEN** the skill tells the user flows are not available on this Atlas and does nothing further
