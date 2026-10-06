## ADDED Requirements

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
