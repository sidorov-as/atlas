## MODIFIED Requirements

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
