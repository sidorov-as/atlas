## ADDED Requirements

### Requirement: Cross-API Endpoint search

`atlas_plugin_apis` SHALL provide a search endpoint returning active Endpoints across every API, matching a query string against `path`, `summary`, or `operation_id`, each result carrying its owning API's reference, name, and title.

#### Scenario: Search matches endpoints across multiple APIs

- **WHEN** the Endpoint search endpoint is called with a query string that matches endpoints belonging to more than one API
- **THEN** results from every matching API are returned, each annotated with its owning API's reference, name, and title

#### Scenario: Search matches on path, summary, or operation_id

- **WHEN** the Endpoint search endpoint is called with a query string that matches only one of an Endpoint's `path`, `summary`, or `operation_id`
- **THEN** that Endpoint is included in the results

#### Scenario: Removed endpoints are excluded by default

- **WHEN** the Endpoint search endpoint is called without an explicit status filter, and a matching Endpoint has `status` `removed`
- **THEN** that Endpoint is excluded from the results

### Requirement: Cross-API Operation search

`atlas_plugin_apis` SHALL provide a search endpoint returning active Operations across every API, matching a query string against `channel_address`, `summary`, or `operation_id`, each result carrying its owning API's reference, name, and title.

#### Scenario: Search matches operations across multiple APIs

- **WHEN** the Operation search endpoint is called with a query string that matches operations belonging to more than one API
- **THEN** results from every matching API are returned, each annotated with its owning API's reference, name, and title

#### Scenario: Search matches on channel_address, summary, or operation_id

- **WHEN** the Operation search endpoint is called with a query string that matches only one of an Operation's `channel_address`, `summary`, or `operation_id`
- **THEN** that Operation is included in the results

#### Scenario: Removed operations are excluded by default

- **WHEN** the Operation search endpoint is called without an explicit status filter, and a matching Operation has `status` `removed`
- **THEN** that Operation is excluded from the results

### Requirement: Endpoint/Operation resolution exposed to other plugins

`atlas_plugin_apis.extension_points` SHALL expose `resolve_endpoint(id)` and `resolve_operation(id)`, each returning the matching `ApiEndpoint`/`ApiOperation` row (including its owning API) for a valid id, and a not-found result for an id that does not exist — without requiring the caller to import `atlas_plugin_apis`'s models directly.

#### Scenario: Resolving an existing endpoint id

- **WHEN** another plugin calls `resolve_endpoint(id)` with an id that matches an existing `ApiEndpoint`
- **THEN** the matching Endpoint, including its owning API, is returned

#### Scenario: Resolving a nonexistent endpoint id

- **WHEN** another plugin calls `resolve_endpoint(id)` with an id that does not match any `ApiEndpoint`
- **THEN** a not-found result is returned rather than an unhandled exception

#### Scenario: Resolving an existing operation id

- **WHEN** another plugin calls `resolve_operation(id)` with an id that matches an existing `ApiOperation`
- **THEN** the matching Operation, including its owning API, is returned
