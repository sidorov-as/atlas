## ADDED Requirements

### Requirement: Step supports Query and Event kinds referencing an Endpoint or Operation

A Flow step MAY carry a `query_ref` (`{api, endpoint, method, path}`) referencing an `atlas_plugin_apis` Endpoint, or an `event_ref` (`{api, operation, direction, channel}`) referencing an Operation, in place of `entity_ref`/`external_label`. A step SHALL carry at most one of `entity_ref`, `external_label`, `query_ref`, and `event_ref`; a step violating this SHALL be rejected on save. On every save, a non-empty `query_ref`/`event_ref` SHALL be resolved: its `api` field SHALL resolve to an existing `api` catalog entity, and its `endpoint`/`operation` id SHALL resolve to an existing Endpoint/Operation belonging to that same API entity; a `query_ref`/`event_ref` that fails either resolution, or whose Endpoint/Operation belongs to a different API than its own `api` field names, SHALL cause the save to be rejected. A `query_ref`/`event_ref` targeting an Endpoint/Operation whose `status` is `removed` SHALL still resolve successfully — removal does not invalidate an existing Flow's reference to it. `method`/`path` (for a Query) and `direction`/`channel` (for an Event) are a point-in-time snapshot captured when the reference is chosen; they are not re-derived from the Endpoint/Operation's current state on save.

#### Scenario: Step with a resolvable query_ref saves successfully

- **WHEN** a Flow is saved with a step whose `query_ref.api` resolves to an existing API entity and whose `query_ref.endpoint` resolves to an Endpoint belonging to that API
- **THEN** the Flow is persisted with that step's `query_ref` intact, including its snapshotted `method`/`path`

#### Scenario: Step with a resolvable event_ref saves successfully

- **WHEN** a Flow is saved with a step whose `event_ref.api` resolves to an existing API entity and whose `event_ref.operation` resolves to an Operation belonging to that API
- **THEN** the Flow is persisted with that step's `event_ref` intact, including its snapshotted `direction`/`channel`

#### Scenario: query_ref/event_ref are mutually exclusive with entity_ref, external_label, and each other

- **WHEN** a Flow is saved with a step that carries more than one of `entity_ref`, `external_label`, `query_ref`, and `event_ref`
- **THEN** the save is rejected

#### Scenario: A query_ref whose endpoint does not exist is rejected

- **WHEN** a Flow is saved with a step whose `query_ref.endpoint` does not resolve to any Endpoint
- **THEN** the save is rejected and no Flow data is persisted or updated

#### Scenario: A query_ref whose endpoint belongs to a different API is rejected

- **WHEN** a Flow is saved with a step whose `query_ref.endpoint` resolves to an Endpoint belonging to an API other than the one named in `query_ref.api`
- **THEN** the save is rejected

#### Scenario: A query_ref/event_ref targeting a removed Endpoint/Operation still saves

- **WHEN** a Flow is saved with a step whose `query_ref`/`event_ref` resolves to an Endpoint/Operation whose `status` is `removed`
- **THEN** the save succeeds

### Requirement: Query/Event resolution degrades clearly when atlas.apis is absent

When the running distribution does not have `atlas.apis` installed, saving a Flow step with a non-empty `query_ref`/`event_ref` SHALL be rejected with a validation message identifying that the APIs plugin is unavailable, rather than an unhandled server error.

#### Scenario: Saving a query_ref without atlas.apis installed

- **WHEN** a Flow is saved with a step carrying a non-empty `query_ref` in a distribution that does not have `atlas.apis` installed
- **THEN** the save is rejected with a validation error explaining that the APIs plugin is required, and no unhandled server error occurs
