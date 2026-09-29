## Purpose

API Endpoints is the `Endpoint` sub-resource of the `api` Entity Kind, owned by the `atlas.apis` plugin. It captures Swagger-like documentation (method, path, request/response shapes) for individual operations of an API, and the UI to browse it, without making `Endpoint` its own registered Entity Kind.

## Requirements

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
An `Endpoint` SHALL store `method`, `path`, optional `operationId`/`summary`/`description`, a `deprecated` flag, optional `tags`, an optional request definition (path/query/header parameters, optional body with content type/schema/example), one or more responses (status code, description, content type, schema, example, and optional headers), an optional `externalDocs` link, and an optional resolved `security` requirement.

#### Scenario: Endpoint with no request body
- **WHEN** an Endpoint has no request body defined
- **THEN** its Request tab shows no request-body section, rather than an empty one

#### Scenario: Endpoint with no parameters
- **WHEN** an Endpoint has no path, query, or header parameters
- **THEN** the corresponding parameter sections are omitted from its Overview and Request tab, rather than shown empty

#### Scenario: Endpoint with no externalDocs or security
- **WHEN** an Endpoint has no `externalDocs` link and no resolved `security` requirement
- **THEN** the corresponding Overview/Details sections are omitted, rather than shown empty

### Requirement: API detail page lists its endpoints
An API's detail page SHALL show a list of its Endpoints, searchable by path/summary/operationId and filterable by HTTP method and deprecated status. This list SHALL show only `active` Endpoints by default.

#### Scenario: Endpoint list search
- **WHEN** a user searches the endpoint list for text matching an endpoint's path, summary, or operationId
- **THEN** only matching endpoints are shown

#### Scenario: Removed endpoints are excluded from the default list
- **WHEN** an API's endpoint list is viewed with no removed-endpoints filter applied
- **THEN** Endpoints with `status=removed` are not shown

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

### Requirement: Endpoint page shows Overview, Request, and Response tabs
An Endpoint's detail page SHALL have Overview, Request, and Response tabs. The Overview tab SHALL show a documentation summary, a Details section (including, when resolvable, Protocol, Base URL, aggregated Consumes/Produces, and Security), path/query/header parameters (if any, each showing its type combined with its format and, when present, its allowed enum values), and a compact response table. The Response tab SHALL let the user select among the endpoint's responses (defaulting to the first `2xx`, or the first response if none is `2xx`) and view that response's content type, schema, headers, and example.

#### Scenario: Response tab defaults to first 2xx
- **WHEN** an Endpoint has responses `401`, `200`, `404`
- **THEN** the Response tab initially selects `200`

#### Scenario: Response tab falls back when no 2xx exists
- **WHEN** an Endpoint's only responses are `400` and `404`
- **THEN** the Response tab initially selects `400`

#### Scenario: Parameter with a format shows type and format together
- **WHEN** a path parameter's schema has `type: string` and `format: uuid`
- **THEN** the Overview and Request tab parameter tables show `string (uuid)`, not `string` alone

#### Scenario: Parameter with an enum shows its allowed values
- **WHEN** a query parameter's schema has an `enum` list
- **THEN** the parameter table shows those allowed values

#### Scenario: Details section omits unresolvable fields rather than showing blanks
- **WHEN** an Endpoint's API has no resolvable base URL/protocol (ambiguous or absent `servers`)
- **THEN** the Details section omits the Protocol/Base URL fields rather than showing empty placeholders

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

### Requirement: A removed Endpoint may be purged
An Endpoint whose `status` is `removed` MAY be permanently deleted via a `Purge` action, requiring the same Purge Grant (or global-admin status) required to purge a whole entity. Purge SHALL be blocked if any active `ServiceEndpointUsage` link still references the Endpoint, and SHALL be permitted, cascading their cleanup, if all remaining `ServiceEndpointUsage` links reference the Endpoint through an already-removed path only. An `active` Endpoint SHALL NOT be purgeable directly — it must be removed first.

#### Scenario: A removed endpoint with no dependents is purged
- **WHEN** a Purge Grant holder invokes Purge on a `removed` Endpoint with no `ServiceEndpointUsage` links
- **THEN** the Endpoint's row is permanently deleted

#### Scenario: Purge is rejected on an active endpoint
- **WHEN** Purge is invoked on an Endpoint whose status is `active`
- **THEN** the request is rejected — the Endpoint must be removed first

#### Scenario: Purge is blocked by an existing dependent link
- **WHEN** Purge is invoked on a `removed` Endpoint that still has a `ServiceEndpointUsage` link
- **THEN** the request is rejected, naming the Service(s) still linked to it

### Requirement: Endpoint not found is distinguished from other failures
Requesting a nonexistent or removed Endpoint SHALL show a distinct "not found" state (with a link back to its API), separate from a general documentation-load failure.

#### Scenario: Nonexistent endpoint id
- **WHEN** a user navigates to an Endpoint id that does not exist
- **THEN** the page shows an endpoint-not-found state with a link back to the parent API, not a generic error
