## Purpose

OpenAPI Endpoint Import parses an `openapi`-typed API's resolved OpenAPI (2.0/3.x) `spec_content` into `ApiEndpoint` rows, triggered on every successful spec resolution (create, patch, or the ingestor's periodic `spec_url` refresh). It owns the create/update/revive/soft-remove upsert rules keyed by `(api, method, path)`, normalizing both OpenAPI 3.x and Swagger 2.0 documents into the same endpoint shape, resolving parameter/request-body/response schema `$ref`s against the document's own `components`/`definitions`, and records parse failures without interrupting the save/refresh path or touching existing `ApiEndpoint` rows.

## Requirements

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
The parser SHALL accept both an `openapi: "3.x"` document and a `swagger: "2.0"` document and normalize each into the same `ApiEndpoint` request/response shape, so no other part of the system needs to know which version produced a given endpoint. This shape SHALL also include, per response, that response's declared headers; per operation, its `externalDocs` link (when present); and per operation, its resolved effective security requirement.

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

#### Scenario: Response headers are imported
- **WHEN** a 3.x response object has a `headers` map
- **THEN** the resulting `ApiEndpoint` response entry includes that header map, keyed by header name

#### Scenario: Operation externalDocs is imported
- **WHEN** an operation (either version) has an `externalDocs` object with a `url`
- **THEN** the resulting `ApiEndpoint.external_docs` has that URL and optional description

#### Scenario: Operation security resolves against securitySchemes
- **WHEN** an operation declares a `security` requirement referencing a scheme defined in the document's `components.securitySchemes` (3.x) or `securityDefinitions` (2.0)
- **THEN** the resulting `ApiEndpoint.security` contains a resolved entry with that scheme's `type` (and `scheme`, for `http`-type schemes), not the raw scheme name

#### Scenario: Operation without its own security inherits the document-level requirement
- **WHEN** an operation has no `security` key of its own and the document declares a top-level `security` requirement
- **THEN** the resulting `ApiEndpoint.security` is resolved from the document-level requirement

#### Scenario: A security requirement referencing an unknown scheme is dropped, not failed
- **WHEN** an operation's `security` requirement references a scheme name absent from `components.securitySchemes`/`securityDefinitions`
- **THEN** that entry is omitted from `ApiEndpoint.security` and the rest of the operation still imports normally

### Requirement: Schema `$ref` values are resolved against components/definitions
A parameter, request body, or response schema that is (or contains) a `$ref` SHALL be resolved against the same document's `components.schemas` (OpenAPI 3.x) or `definitions` (Swagger 2.0), recursively — including a `$ref` nested inside an otherwise-inline schema's properties, not only a schema that is a bare `$ref` at the top level. A sibling key found alongside that `$ref` (e.g. a local `description` override) SHALL be preserved: it is overlaid on top of the resolved target's own content (the sibling wins on a key-name collision), uniformly for OpenAPI 3.0, 3.1, and Swagger 2.0 — this plugin does not distinguish OpenAPI's minor versions, so it does not attempt to apply 3.1's JSON-Schema-accurate `$ref`-with-siblings semantics only to 3.1 documents. The only cases where a `$ref` is left unresolved are: the pointer does not resolve to anything defined in the document, or resolving it would re-enter a `$ref` already being expanded along the same resolution path (a reference cycle) — in either case, any sibling key the `$ref` carried is still preserved on the returned (unresolved) node.

#### Scenario: A response schema that is a $ref is resolved
- **WHEN** an operation's response schema is `{"$ref": "#/components/schemas/Booking"}` and `#/components/schemas/Booking` is an inline object schema
- **THEN** the resulting `ApiEndpoint` response's schema has that schema's expanded `properties`, not just `ref="#/components/schemas/Booking"`

#### Scenario: A request body schema $ref is resolved
- **WHEN** a 3.x operation's `requestBody.content['application/json'].schema` is `{"$ref": "#/components/schemas/CreateBookingRequest"}` pointing at an inline object schema
- **THEN** the resulting `ApiEndpoint.request.body.schema` is that schema's expanded content

#### Scenario: A nested property $ref inside an otherwise-inline schema is resolved
- **WHEN** an inline object schema has a property whose value is `{"$ref": "#/components/schemas/Money"}` pointing at an inline schema
- **THEN** that property's schema in the resulting `ApiEndpoint` request/response is the expanded `Money` schema, not a bare `$ref`

#### Scenario: A Swagger 2.0 schema $ref against definitions is resolved
- **WHEN** a 2.0 operation's response schema is `{"$ref": "#/definitions/Error"}` and `#/definitions/Error` is an inline object schema
- **THEN** the resulting response's schema is that schema's expanded content

#### Scenario: A genuinely unresolvable schema $ref is left unresolved
- **WHEN** a schema's `$ref` points at something not defined anywhere in the document
- **THEN** that occurrence remains an unresolved `{"$ref": ...}` node, exactly as today, and the rest of the operation still imports normally

#### Scenario: A self-referential schema stops at the cycle, not before
- **WHEN** a schema property's own (possibly nested) `$ref` chain would resolve back to a schema currently being expanded on the same path
- **THEN** resolution expands normally up to that point, and that occurrence is left as an unresolved `{"$ref": ...}` node instead of recursing again

#### Scenario: A sibling key next to a schema $ref is preserved
- **WHEN** a request/response schema is `{"$ref": "#/components/schemas/Booking", "description": "override"}` and `#/components/schemas/Booking` is an inline object schema with no `description` of its own
- **THEN** the resulting schema has `Booking`'s expanded `properties` plus `description: "override"` overlaid on top — not a bare `$ref` label, and not `Booking`'s content with the sibling silently dropped

#### Scenario: A sibling key survives a cycle or a dangling reference
- **WHEN** a schema is `{"$ref": "#/components/schemas/X", "description": "override"}` and resolving `X` either re-enters a `$ref` already on the current resolution path (a cycle) or does not resolve to anything defined in the document (dangling)
- **THEN** the returned node is still `{"$ref": "#/components/schemas/X", "description": "override"}` — the sibling `description` is not lost just because the `$ref` itself couldn't be expanded further. (This holds because OpenAPI always resolves with sibling-preservation enabled; the AsyncAPI-side requirement discards siblings in this same cycle/dangling situation instead — see that capability's own scenario.)

#### Scenario: A sibling value that itself contains a $ref is resolved before being overlaid
- **WHEN** a schema is `{"$ref": "#/components/schemas/Booking", "not": {"$ref": "#/components/schemas/CancelledBooking"}}` and both targets are inline object schemas
- **THEN** the resulting schema has `Booking`'s expanded content with a `not` key overlaid whose own value is `CancelledBooking`'s expanded content, not a bare `{"$ref": "#/components/schemas/CancelledBooking"}` left inside the overlaid sibling

#### Scenario: A $ref inside example/default/enum/const data is never touched
- **WHEN** a request/response schema has an `example` (or `default`, `enum`, `const`) value that itself contains a key literally named `$ref` (e.g. `example: {"$ref": "not-a-reference"}`), as arbitrary data an author wrote, not a schema reference
- **THEN** that value is stored exactly as written, untouched by resolution — only `properties`/`items`/`additionalProperties`/`allOf`/`oneOf`/`anyOf`/`not` are ever walked looking for a `$ref` to resolve

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

### Requirement: Document-level servers resolve to a base URL and protocol only when unambiguous
The parser SHALL populate `ApiDetails`' resolved base URL and protocol only when the document unambiguously identifies one server (a 3.x document declaring exactly one entry in its top-level `servers` list, or a 2.0 document's single `host`+`basePath` with exactly one `schemes` entry); otherwise both SHALL be left empty rather than guessed. This mirrors `asyncapi-operation-import`'s existing "Channel protocol is resolved only when unambiguous" rule.

#### Scenario: Single 3.x server resolves base URL and protocol
- **WHEN** a 3.x document declares exactly one entry in its top-level `servers` list
- **THEN** `ApiDetails`' resolved base URL and protocol are populated from that server's `url`

#### Scenario: Multiple 3.x servers leave base URL and protocol unresolved
- **WHEN** a 3.x document declares more than one entry in its top-level `servers` list
- **THEN** `ApiDetails`' resolved base URL and protocol are left empty rather than guessing among the candidates

#### Scenario: Swagger 2.0 host/basePath/schemes resolves base URL and protocol
- **WHEN** a 2.0 document declares `host`, `basePath`, and exactly one `schemes` entry
- **THEN** `ApiDetails`' resolved base URL and protocol are populated from those fields

#### Scenario: Swagger 2.0 multiple schemes leave protocol unresolved
- **WHEN** a 2.0 document declares more than one `schemes` entry
- **THEN** `ApiDetails`' resolved protocol is left empty; the base URL (host+basePath, scheme-independent) may still resolve
