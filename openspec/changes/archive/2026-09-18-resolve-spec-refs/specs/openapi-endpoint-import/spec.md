## RENAMED Requirements
- FROM: `### Requirement: Schema `$ref` values are stored unresolved`
- TO: `### Requirement: Schema `$ref` values are resolved against components/definitions`

## MODIFIED Requirements

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
