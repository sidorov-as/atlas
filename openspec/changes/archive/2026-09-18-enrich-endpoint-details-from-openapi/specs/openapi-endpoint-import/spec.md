## MODIFIED Requirements

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

## ADDED Requirements

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
