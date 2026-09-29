## ADDED Requirements

### Requirement: Endpoint is a child resource of API, not a registered Entity Kind
An `Endpoint` SHALL belong to exactly one `API` entity and SHALL NOT be a registered Entity Kind — it has no `kind_id`, no independent owner/team/tags/visibility, and no top-level catalog entity route; it inherits owner/domain/visibility from its API and is addressed only via routes nested under that API.

#### Scenario: Endpoint has no top-level entity route
- **WHEN** a user has an Endpoint's id
- **THEN** there is no `/catalog/entities/endpoint/{id}`-style route for it; it is only reachable via `/apis/{apiId}/endpoints/{endpointId}`

#### Scenario: Endpoint documentation displays its API's owner/domain/visibility
- **WHEN** an Endpoint's Overview is displayed
- **THEN** the Owner, Domain, and Visibility shown are the parent API's values, not independently stored on the Endpoint

### Requirement: Endpoint has a stable identity independent of its business key
Each `Endpoint` SHALL have its own identifier that does not change if its `method` or `path` changes, and SHALL be unique within its API by `(method, path)`.

#### Scenario: Endpoint id is stable across a path edit
- **WHEN** an Endpoint's `path` is edited after creation
- **THEN** its id is unchanged and existing links to it (URLs, `ServiceEndpointUsage` rows) remain valid

#### Scenario: Duplicate method+path within an API is rejected
- **WHEN** a second Endpoint is created on the same API with the same `method` and exact `path` as an existing Endpoint
- **THEN** the creation is rejected

#### Scenario: Same method+path is allowed across different APIs
- **WHEN** two different APIs each have an Endpoint with the same `method` and `path`
- **THEN** both creations succeed, since uniqueness is scoped per API

### Requirement: Endpoint captures request and response documentation
An `Endpoint` SHALL store `method`, `path`, optional `operationId`/`summary`/`description`, a `deprecated` flag, optional `tags`, an optional request definition (path/query/header parameters, optional body with content type/schema/example), and one or more responses (status code, description, content type, schema, example).

#### Scenario: Endpoint with no request body
- **WHEN** an Endpoint has no request body defined
- **THEN** its Request tab shows no request-body section, rather than an empty one

#### Scenario: Endpoint with no parameters
- **WHEN** an Endpoint has no path, query, or header parameters
- **THEN** the corresponding parameter sections are omitted from its Overview and Request tab, rather than shown empty

### Requirement: API detail page lists its endpoints
An API's detail page SHALL show a list of its Endpoints, searchable by path/summary/operationId and filterable by HTTP method and deprecated status. This list SHALL show only `active` Endpoints by default.

#### Scenario: Endpoint list search
- **WHEN** a user searches the endpoint list for text matching an endpoint's path, summary, or operationId
- **THEN** only matching endpoints are shown

#### Scenario: Removed endpoints are excluded from the default list
- **WHEN** an API's endpoint list is viewed with no removed-endpoints filter applied
- **THEN** Endpoints with `status=removed` are not shown

### Requirement: Endpoint documentation is entered administratively in this change
Creating or editing an `Endpoint`'s documentation SHALL NOT be available through any self-service, permission-gated API or UI in this change; endpoint data is entered through Django admin or fixtures/seed data.

#### Scenario: No create/edit endpoint exists
- **WHEN** a client requests to create or update an `Endpoint` through the catalog API
- **THEN** no such operation is exposed — only reading (list, detail) is available

### Requirement: Removing an endpoint is soft, preserving existing dependency links
Removing an `Endpoint` SHALL set its status to `removed` rather than deleting its row, and SHALL NOT delete any `ServiceEndpointUsage` rows that reference it. A `removed` Endpoint SHALL remain visible in a dedicated section separate from an API's default (active) endpoint list, and any view of its existing Service links SHALL show a visible warning that the endpoint has been removed.

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

### Requirement: Endpoint page shows Overview, Request, and Response tabs
An Endpoint's detail page SHALL have Overview, Request, and Response tabs. The Overview tab SHALL show a documentation summary, protocol/details, path/query/header parameters (if any), and a compact response table. The Response tab SHALL let the user select among the endpoint's responses (defaulting to the first `2xx`, or the first response if none is `2xx`) and view that response's content type, schema, and example.

#### Scenario: Response tab defaults to first 2xx
- **WHEN** an Endpoint has responses `401`, `200`, `404`
- **THEN** the Response tab initially selects `200`

#### Scenario: Response tab falls back when no 2xx exists
- **WHEN** an Endpoint's only responses are `400` and `404`
- **THEN** the Response tab initially selects `400`

### Requirement: Deprecated endpoints remain fully documented and linkable
A `deprecated` Endpoint SHALL display a visible deprecation indicator on its header, and SHALL continue to show its full documentation and any existing Service links rather than being hidden or archived.

#### Scenario: Deprecated endpoint still shows its consumers
- **WHEN** an Endpoint marked `deprecated` has existing Service links
- **THEN** its Linked Services and consumers graph continue to display those Services unchanged

### Requirement: HTTP method and status code are not distinguished by color alone
Method badges (`GET`/`POST`/`PUT`/`PATCH`/`DELETE`/`HEAD`/`OPTIONS`) and response status-code indicators SHALL always include the method/code text alongside any semantic color, never color alone.

#### Scenario: Method badge includes text
- **WHEN** a `POST` endpoint's method badge is rendered
- **THEN** the badge displays the text "POST" regardless of its background color

### Requirement: Endpoint not found is distinguished from other failures
Requesting a nonexistent or removed Endpoint SHALL show a distinct "not found" state (with a link back to its API), separate from a general documentation-load failure.

#### Scenario: Nonexistent endpoint id
- **WHEN** a user navigates to an Endpoint id that does not exist
- **THEN** the page shows an endpoint-not-found state with a link back to the parent API, not a generic error
