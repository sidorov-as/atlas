## MODIFIED Requirements

### Requirement: API spec source model
An API entity SHALL record its spec via an explicit source discriminator (`none`, `inline`, or `url`) plus a single resolved-content field (`spec_content`) that every consumer reads, regardless of which source produced it. When `spec_source` is `inline`, the submitted `spec_content` SHALL be bounded to a fixed maximum length, enforced independently of any size limit applied to `url`-sourced content during fetch.

#### Scenario: Setting inline spec content
- **WHEN** a user pastes or uploads spec text with source `inline`
- **THEN** `spec_content` is set to that text immediately and `spec_source` is `inline`

#### Scenario: Setting a spec URL resolves it immediately
- **WHEN** a user saves an API with `spec_source` set to `url` and a `spec_url`
- **THEN** the server fetches `spec_url` once synchronously and populates `spec_content` and `spec_resolved_at` from the response

#### Scenario: Clearing the spec source
- **WHEN** a user sets `spec_source` to `none`
- **THEN** `spec_content`, `spec_url`, `spec_resolved_at`, and `spec_resolve_failed` are all cleared

#### Scenario: Oversized inline spec content is rejected
- **WHEN** a user saves an API with `spec_source` set to `inline` and `spec_content` longer than its declared maximum length
- **THEN** the request is rejected with a validation error and the API's stored `spec_content` is unchanged
