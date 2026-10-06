## Purpose

APIs is the optional plugin that provides the `api` Entity Kind, extracted out of Standard Catalog so a distribution can omit it. It declares a manifest dependency on Standard Catalog (Components reference APIs via `providesApis`/`consumesApis`), and Standard Catalog degrades gracefully — validating those reference fields as empty rather than erroring — when APIs is not selected.

## Requirements

### Requirement: API is an optional plugin-provided kind
The API Entity Kind SHALL be provided entirely by the `atlas.apis` plugin; a distribution MAY omit it.

#### Scenario: Distribution without atlas.apis composes successfully
- **WHEN** a distribution selects `atlas.standard-catalog` but not `atlas.apis`
- **THEN** composition succeeds, and no `api` kind is registered

### Requirement: APIs plugin declares a manifest dependency on Standard Catalog
`atlas.apis` SHALL declare a manifest dependency on `atlas.standard-catalog` within a compatible version range; composition SHALL fail if that dependency isn't satisfied.

#### Scenario: Compatible Standard Catalog satisfies the dependency
- **WHEN** a distribution selects `atlas.apis` and a version of `atlas.standard-catalog` within its declared compatible range
- **THEN** composition succeeds

### Requirement: Cross-plugin API references degrade gracefully when APIs is absent
Standard Catalog's `providesApis`/`consumesApis` reference fields SHALL be valid and empty, not an error, when `atlas.apis` is not selected.

#### Scenario: providesApis is inert without the APIs plugin
- **WHEN** `atlas.apis` is not selected
- **THEN** a Component's `providesApis`/`consumesApis` fields accept no values and any pre-existing values are treated as referencing an absent kind, without crashing the Component's own CRUD or detail page

### Requirement: API spec is an upload target
The APIs plugin SHALL register `(api, spec)` as an upload target. The adapter SHALL apply the uploaded body as the API's spec content through the same spec source application used for inline content, subject to the same size, depth, and node limits, and SHALL trigger the same endpoint or operation synchronization. A body that fails the spec acceptance check SHALL be rejected with the failure reason; the stored spec SHALL remain unchanged. A successful upload SHALL return a summary with the detected spec kind and the number of endpoints or operations synchronized.

#### Scenario: Valid OpenAPI upload
- **WHEN** a client uploads a valid OpenAPI document to an API's spec ticket
- **THEN** the spec content is stored, endpoints are synchronized, and the summary reports the spec kind and endpoint count

#### Scenario: Valid AsyncAPI upload
- **WHEN** a client uploads a valid AsyncAPI document
- **THEN** operations are synchronized and the summary reports the operation count

#### Scenario: Unacceptable body is rejected
- **WHEN** a client uploads an empty body or a document that exceeds the parse limits
- **THEN** the upload is rejected with the reason and the stored spec is unchanged

#### Scenario: Upload sets the spec source
- **WHEN** a client uploads a spec to an API whose spec source was `url`
- **THEN** the API's spec source becomes inline content, consistent with writing `spec_content` directly
