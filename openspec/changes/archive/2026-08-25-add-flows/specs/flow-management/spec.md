## ADDED Requirements

### Requirement: Flow belongs to exactly one home System
A Flow SHALL have a required, non-nullable reference to exactly one `System` (its home system). A Flow's `name` SHALL be unique within its home system. Deleting a System that is the home system of one or more Flows SHALL be blocked until those Flows are deleted or reassigned.

#### Scenario: Flow created with a home system
- **WHEN** a Flow is created with a valid home `system` reference, a unique `name` within that system, and a `steps` array
- **THEN** the Flow is persisted and appears under that system

#### Scenario: Flow requires a home system
- **WHEN** a Flow is created without a `system` reference
- **THEN** the request is rejected

#### Scenario: Duplicate name within the same system is rejected
- **WHEN** a Flow is created with a `name` that already exists on another Flow whose home system is the same
- **THEN** the request is rejected

#### Scenario: Deleting a system with flows is blocked
- **WHEN** an attempt is made to delete a System that is the home system of at least one Flow
- **THEN** the deletion is rejected until those Flows are deleted or reassigned to a different home system

### Requirement: Step entity references are validated against the catalog
Each step in a Flow's `steps` array MAY carry an `entity_ref` (a `kind:name` string using the catalog's existing ref grammar). On every save, every non-empty `entity_ref` SHALL be resolved against the catalog; a ref that does not resolve to an existing entity SHALL cause the save to be rejected. A step's `entity_ref` is a validated reference only — it is not stored as a foreign key and does not appear in the catalog's derived relations.

#### Scenario: Step with a resolvable entity_ref saves successfully
- **WHEN** a Flow is saved with a step whose `entity_ref` (e.g. `component:checkout-service`) resolves to an existing catalog entity
- **THEN** the Flow is persisted with that step's `entity_ref` intact

#### Scenario: Step with an unresolvable entity_ref is rejected
- **WHEN** a Flow is saved with a step whose `entity_ref` does not resolve to any existing catalog entity
- **THEN** the save is rejected and no Flow data is persisted or updated

#### Scenario: Step without an entity_ref is allowed
- **WHEN** a Flow is saved with a step that omits `entity_ref`
- **THEN** the save succeeds — a step is not required to reference a catalog entity

### Requirement: Step transitions form a strict divergence-only tree
Each step MAY declare a transition to the next step(s) via `next_step` (a single `{id, label}`) or `next_steps` (an array of `{id, label}` for branching). Across a Flow's entire `steps` array, a given step id SHALL be the target of at most one incoming transition — branches MAY diverge but MUST NOT reconverge on a shared step. A save that would violate this SHALL be rejected.

#### Scenario: Divergence-only steps save successfully
- **WHEN** a Flow is saved where every step id is the target of zero or one incoming `next_step`/`next_steps` entries
- **THEN** the Flow is persisted

#### Scenario: Reconverging branches are rejected
- **WHEN** a Flow is saved where two different steps each declare a transition targeting the same step id
- **THEN** the save is rejected

#### Scenario: A transition to a nonexistent step id is rejected
- **WHEN** a Flow is saved where a `next_step`/`next_steps` entry targets a step id that does not exist elsewhere in the same `steps` array
- **THEN** the save is rejected

### Requirement: Flow list API supports filtering by system and team
The Flow list API SHALL support filtering results by home `system` and by the home system's owning team (Group).

#### Scenario: Filter flows by system
- **WHEN** the Flow list API is called with a `system` filter
- **THEN** only Flows whose home system matches are returned

#### Scenario: Filter flows by team
- **WHEN** the Flow list API is called with a `team` filter
- **THEN** only Flows whose home system's owner matches that team are returned

### Requirement: Flows are reachable from the catalog sidebar
The web UI SHALL expose a "Flows" item in the primary sidebar navigation, leading to a list page showing all Flows with search, a System filter, and a Team filter, and a "create Flow" action.

#### Scenario: Flows nav item is present
- **WHEN** a signed-in user views the sidebar
- **THEN** a "Flows" navigation item is present alongside Systems, Components, Resources, APIs, and Teams

#### Scenario: List page filters by system and team
- **WHEN** a user selects a System or a Team filter on the Flows list page
- **THEN** only Flows matching that filter are shown

### Requirement: Flow detail page renders and edits the step diagram
A Flow's detail page SHALL render its `steps` as a left-to-right tree diagram, computed and laid out entirely client-side from the `steps` data (independent of the catalog's C4 diagram endpoint). The page SHALL provide a JSON editor over the `steps` array with a live preview that re-renders the diagram as the JSON is edited, and SHALL allow saving changes.

#### Scenario: Detail page renders the diagram
- **WHEN** a user opens a Flow's detail page
- **THEN** its steps are rendered as a left-to-right tree diagram reflecting each step's transitions

#### Scenario: Live preview updates as the JSON is edited
- **WHEN** a user edits the `steps` JSON in the detail page's editor
- **THEN** the diagram preview re-renders to reflect the edited steps without requiring a save

#### Scenario: Invalid edits are rejected on save
- **WHEN** a user attempts to save `steps` JSON that fails entity-ref resolution or the strict-tree rule
- **THEN** the save is rejected and the user is shown the validation failure
