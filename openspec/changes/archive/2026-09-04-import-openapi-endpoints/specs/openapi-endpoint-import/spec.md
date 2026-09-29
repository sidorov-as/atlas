## ADDED Requirements

### Requirement: Spec resolution triggers endpoint sync
Whenever an `ApiDetails` record is saved with `type='openapi'` and a non-empty `spec_content`, the system SHALL parse `spec_content` and synchronize that API's `ApiEndpoint` rows to match it, regardless of which write path produced the save (create, patch, or the ingestor's periodic `spec_url` refresh).

#### Scenario: Sync runs after creating an API with an inline OpenAPI spec
- **WHEN** a user creates an `openapi`-typed API with `spec_source='inline'` and a valid OpenAPI document as `spec_content`
- **THEN** `ApiEndpoint` rows are created for every operation in that document before the create request completes

#### Scenario: Sync runs after the periodic refresh of a URL-sourced spec
- **WHEN** the ingestor's periodic refresh re-fetches a `spec_url` and the response is a valid, changed OpenAPI document
- **THEN** that API's `ApiEndpoint` rows are synchronized to the newly-fetched document within the same refresh pass, without any code outside `atlas_plugin_apis` invoking the sync explicitly

#### Scenario: Non-openapi-typed APIs are never synced
- **WHEN** an API's `type` is `grpc`, `asyncapi`, or `graphql`
- **THEN** no endpoint sync is attempted and its `ApiEndpoint` rows (if any, e.g. from prior manual authoring) are left untouched

#### Scenario: Empty spec content is not synced
- **WHEN** an `openapi`-typed API's `spec_content` is empty (`spec_source='none'`, or a URL/inline source that resolved to nothing)
- **THEN** no endpoint sync is attempted and existing `ApiEndpoint` rows are left untouched

### Requirement: Endpoint lifecycle is derived from diffing the parsed spec against existing endpoints
For an `openapi`-typed API, the system SHALL reconcile parsed operations against existing `ApiEndpoint` rows keyed by `(api, method, path)`: creating rows for new operations, updating fields in place for changed operations (preserving `id` and any `ServiceEndpointUsage` links), reviving a `removed` row whose operation reappears, and setting `status='removed'` on an `active` row whose operation disappears. No `ApiEndpoint` row is ever deleted by this process, and no `ServiceEndpointUsage` row is ever deleted or modified by it.

#### Scenario: A new operation creates an endpoint
- **WHEN** a re-parsed spec contains a `method`+`path` combination with no existing `ApiEndpoint` on that API
- **THEN** a new `ApiEndpoint` is created with `status='active'` and the parsed documentation fields

#### Scenario: A changed operation updates the existing endpoint without changing its identity
- **WHEN** a re-parsed spec's operation for an existing `active` endpoint has a different `summary`, `description`, `deprecated`, `tags`, `request`, or `responses` than what's stored
- **THEN** the existing `ApiEndpoint` row is updated in place; its `id` is unchanged and any `ServiceEndpointUsage` rows referencing it remain valid

#### Scenario: An operation missing from the new spec is soft-removed
- **WHEN** a re-parsed spec no longer contains a `method`+`path` combination that a previously `active` `ApiEndpoint` on that API has
- **THEN** that `ApiEndpoint`'s `status` becomes `removed`, the row is not deleted, and any `ServiceEndpointUsage` rows referencing it are not deleted

#### Scenario: A previously removed operation that reappears is revived
- **WHEN** a re-parsed spec now contains a `method`+`path` combination matching a `removed` `ApiEndpoint` on that API
- **THEN** that `ApiEndpoint`'s `status` becomes `active` again, its documentation fields are updated from the reappeared operation, and its `id` and any existing `ServiceEndpointUsage` rows are unchanged

### Requirement: Both OpenAPI 3.x and Swagger 2.0 are parsed into one endpoint shape
The parser SHALL accept both an `openapi: "3.x"` document and a `swagger: "2.0"` document and normalize each into the same `ApiEndpoint` request/response shape, so no other part of the system needs to know which version produced a given endpoint.

#### Scenario: OpenAPI 3.x requestBody is imported
- **WHEN** a 3.x operation has a `requestBody.content['application/json'].schema`
- **THEN** the resulting `ApiEndpoint.request.body` has `content_type='application/json'` and that schema

#### Scenario: Swagger 2.0 body parameter is imported
- **WHEN** a 2.0 operation has an `in: body` parameter with a `schema`
- **THEN** the resulting `ApiEndpoint.request.body` has that schema, with `content_type` taken from the operation's (or document's) `consumes`, defaulting to `application/json` when absent

#### Scenario: Swagger 2.0 formData parameters are imported as one body schema
- **WHEN** a 2.0 operation has one or more `in: formData` parameters
- **THEN** the resulting `ApiEndpoint.request.body` has an `object` schema whose `properties` are the form fields

#### Scenario: Path, query, and header parameters are imported from either version
- **WHEN** an operation (either version) has parameters with `in: path`, `in: query`, or `in: header`
- **THEN** each becomes an entry in `ApiEndpoint.request.parameters` with the matching `location`, `name`, `required`, and `schema`

#### Scenario: Cookie parameters are dropped without failing the operation
- **WHEN** a 3.x operation has a parameter with `in: cookie`
- **THEN** that parameter is omitted from `ApiEndpoint.request.parameters` and the rest of the operation still imports normally

### Requirement: Schema `$ref` values are stored unresolved
A parameter, request body, or response schema that is (or contains) a `$ref` SHALL be stored with that `$ref` string verbatim; the parser SHALL NOT resolve it against `components`/`definitions`.

#### Scenario: A response schema that is a $ref is stored as-is
- **WHEN** an operation's response schema is `{"$ref": "#/components/schemas/Booking"}`
- **THEN** the resulting `ApiEndpoint` response's schema has `ref="#/components/schemas/Booking"` and no expanded `properties`

### Requirement: Parse failures never interrupt the save/refresh path and are recorded, not silent
A spec that fails to parse as recognizable OpenAPI SHALL NOT raise an exception out of the create, patch, or periodic-refresh path, and SHALL NOT modify any existing `ApiEndpoint` row for that API. A single operation within an otherwise-parseable spec that fails to map to the endpoint shape SHALL be skipped without failing the rest of the spec's import. Every successful sync SHALL update `ApiDetails.endpoints_synced_at` and clear `ApiDetails.endpoints_sync_failed`; every spec-level failure SHALL set `ApiDetails.endpoints_sync_failed` without changing `endpoints_synced_at`.

#### Scenario: An unparseable spec leaves existing endpoints untouched
- **WHEN** an `openapi`-typed API's `spec_content` has no recognizable `openapi`/`swagger` version key or no usable `paths`
- **THEN** the save or refresh completes successfully, existing `ApiEndpoint` rows for that API are unchanged, and `ApiDetails.endpoints_sync_failed` becomes `true`

#### Scenario: One malformed operation doesn't block the rest of the spec
- **WHEN** a spec has ten valid operations and one operation whose shape the parser can't map
- **THEN** the nine valid operations are synced normally and the malformed one is skipped and logged, without setting `endpoints_sync_failed`

#### Scenario: A successful sync clears a prior failure
- **WHEN** an API previously had `endpoints_sync_failed=true` and its spec is re-resolved into a document that now parses successfully
- **THEN** `endpoints_sync_failed` becomes `false` and `endpoints_synced_at` is updated to the current time
