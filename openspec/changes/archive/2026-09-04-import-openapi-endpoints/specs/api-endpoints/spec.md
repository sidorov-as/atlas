## MODIFIED Requirements

### Requirement: Endpoint documentation is entered administratively in this change
Creating or editing an `Endpoint`'s documentation SHALL NOT be available through any self-service, permission-gated API or UI; endpoint data is entered through Django admin, fixtures/seed data, or — for an `openapi`-typed API — the OpenAPI importer (`openapi-endpoint-import` capability), which writes `ApiEndpoint` rows as a system-triggered side effect of that API's spec resolving, not as a client-facing create/edit operation.

#### Scenario: No create/edit endpoint exists
- **WHEN** a client requests to create or update an `Endpoint` through the catalog API
- **THEN** no such operation is exposed — only reading (list, detail) is available

#### Scenario: Importer writes are not a self-service operation
- **WHEN** an `openapi`-typed API's spec resolves and its parsed operations differ from its existing `ApiEndpoint` rows
- **THEN** the resulting `ApiEndpoint` creates/updates happen without any client request having asked to create or edit an `Endpoint`, and no create/edit operation is exposed through the catalog API as a result

### Requirement: Removing an endpoint is soft, preserving existing dependency links
Removing an `Endpoint` SHALL set its status to `removed` rather than deleting its row, and SHALL NOT delete any `ServiceEndpointUsage` rows that reference it, regardless of whether the removal was triggered by an administrator or by the OpenAPI importer noticing the operation is no longer in a re-parsed spec. A `removed` Endpoint SHALL remain visible in a dedicated section separate from an API's default (active) endpoint list, and any view of its existing Service links SHALL show a visible warning that the endpoint has been removed. A `removed` Endpoint whose operation reappears in a later re-parsed spec SHALL become `active` again without losing its existing `ServiceEndpointUsage` links.

#### Scenario: Removing an endpoint preserves its links
- **WHEN** an Endpoint with existing `ServiceEndpointUsage` links is removed
- **THEN** its status becomes `removed`, its row and all of its existing links remain in the database, and no `ServiceEndpointUsage` row referencing it is deleted

#### Scenario: Removed endpoint is still reachable
- **WHEN** an API has one or more `removed` Endpoints
- **THEN** those Endpoints are visible in a "Removed endpoints" section, distinct from the default active-endpoint list

#### Scenario: Removed endpoint's page warns about existing dependents
- **WHEN** a `removed` Endpoint that still has `ServiceEndpointUsage` links is viewed
- **THEN** its page shows a visible warning stating the endpoint was removed and naming how many Services still declare a dependency on it

#### Scenario: A removed endpoint cannot receive new links
- **WHEN** a user views a `removed` Endpoint's page
- **THEN** no Link Service action is offered

#### Scenario: An endpoint disappearing from a re-parsed spec is removed the same way
- **WHEN** an `openapi`-typed API's spec is re-resolved and no longer contains an operation matching a previously `active` Endpoint's `method`+`path`
- **THEN** that Endpoint's status becomes `removed`, its row is not deleted, and its existing `ServiceEndpointUsage` rows are preserved

#### Scenario: A removed endpoint revives when the spec adds it back
- **WHEN** an `openapi`-typed API's spec is re-resolved and now contains an operation matching a previously `removed` Endpoint's `method`+`path`
- **THEN** that Endpoint's status becomes `active`, its documentation fields are updated from the reappeared operation, and its existing `ServiceEndpointUsage` links are unchanged
