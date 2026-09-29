## ADDED Requirements

### Requirement: API spec source model
An API entity SHALL record its spec via an explicit source discriminator (`none`, `inline`, or `url`) plus a single resolved-content field (`spec_content`) that every consumer reads, regardless of which source produced it.

#### Scenario: Setting inline spec content
- **WHEN** a user pastes or uploads spec text with source `inline`
- **THEN** `spec_content` is set to that text immediately and `spec_source` is `inline`

#### Scenario: Setting a spec URL resolves it immediately
- **WHEN** a user saves an API with `spec_source` set to `url` and a `spec_url`
- **THEN** the server fetches `spec_url` once synchronously and populates `spec_content` and `spec_resolved_at` from the response

#### Scenario: Clearing the spec source
- **WHEN** a user sets `spec_source` to `none`
- **THEN** `spec_content`, `spec_url`, `spec_resolved_at`, and `spec_resolve_failed` are all cleared

### Requirement: Periodic refresh of URL-sourced specs
For every API with `spec_source` of `url`, the ingestor's poll loop SHALL periodically re-fetch `spec_url` and overwrite `spec_content` only when the response is non-empty and parses as YAML-or-JSON; a failed or implausible fetch SHALL leave the existing `spec_content` untouched and flag the failure, without halting the ingestion pass.

#### Scenario: Successful refresh updates the snapshot
- **WHEN** a periodic refresh fetches `spec_url` and the response is non-empty and parses as YAML-or-JSON
- **THEN** `spec_content` is overwritten with the new response, `spec_resolved_at` is updated, and `spec_resolve_failed` is set to false

#### Scenario: Failed refresh preserves the last-good snapshot
- **WHEN** a periodic refresh's fetch fails, returns an empty body, or returns a body that does not parse as YAML-or-JSON
- **THEN** `spec_content` is left unchanged, `spec_resolve_failed` is set to true, and the failure is logged without stopping the refresh pass for other APIs

#### Scenario: Refresh applies regardless of how the API entity itself was created
- **WHEN** an API has `spec_source` of `url`
- **THEN** it is refreshed on the same schedule whether the API entity is manually created or YAML-managed

### Requirement: Type-conditional spec rendering with universal download
An API's detail page SHALL render `spec_content` through a documentation viewer when one exists for its `type`, and SHALL always offer a raw download of `spec_content` regardless of type, source, or renderer availability.

#### Scenario: OpenAPI spec renders as documentation
- **WHEN** an API's `type` is `openapi` and `spec_content` is non-empty
- **THEN** the detail page renders it using an OpenAPI documentation viewer

#### Scenario: AsyncAPI spec renders as documentation
- **WHEN** an API's `type` is `asyncapi` and `spec_content` is non-empty
- **THEN** the detail page renders it using an AsyncAPI documentation viewer

#### Scenario: Unrendered types offer download only
- **WHEN** an API's `type` is `grpc` or `graphql`
- **THEN** the detail page offers a download of `spec_content` and does not attempt to render it as documentation

#### Scenario: A render failure falls back to download
- **WHEN** an API's `type` has a documentation viewer but rendering `spec_content` throws (e.g. content is not valid YAML/JSON or not a recognizable document of that type)
- **THEN** the detail page falls back to offering a download of `spec_content` instead of showing a broken or blank view

#### Scenario: No download action when there is no content
- **WHEN** an API's `spec_content` is empty
- **THEN** the detail page offers neither a rendered view nor a download action

### Requirement: Stale spec indicator
An API's detail page SHALL visibly indicate when `spec_resolve_failed` is true, explaining that the displayed spec is the last successfully fetched copy.

#### Scenario: Failed refresh shows a warning indicator
- **WHEN** an API's `spec_resolve_failed` is true
- **THEN** the detail page shows a danger-themed label with a tooltip explaining that the last refresh of `spec_url` failed and the shown content is stale

#### Scenario: No indicator when the spec is current
- **WHEN** an API's `spec_resolve_failed` is false
- **THEN** the detail page shows no stale-spec indicator
