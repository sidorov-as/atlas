## MODIFIED Requirements

### Requirement: API spec source model
An API entity SHALL record its spec via an explicit source discriminator (`none`, `inline`, or `url`) plus a single resolved-content field (`spec_content`) that every consumer reads, regardless of which source produced it.

#### Scenario: Setting inline spec content
- **WHEN** a user pastes or uploads spec text with source `inline`
- **THEN** `spec_content` is set to that text immediately and `spec_source` is `inline`

#### Scenario: Setting a spec URL resolves it immediately, subject to fetch safety constraints
- **WHEN** a user saves an API with `spec_source` set to `url` and a `spec_url`
- **THEN** the server fetches `spec_url` once synchronously, only over HTTPS (or an operator-allowlisted exception), only connecting to a publicly-routable non-reserved address with redirects re-validated the same way, within a bounded response size, and populates `spec_content` and `spec_resolved_at` from the response when the fetch succeeds under those constraints

#### Scenario: A fetch that violates a safety constraint is treated as a failed resolution
- **WHEN** `spec_url` is not HTTPS and not allowlisted, resolves (directly or via redirect) to a private, loopback, link-local, or otherwise reserved address, or its response exceeds the configured size limit
- **THEN** the fetch is rejected, `spec_resolve_failed` is set to true, and any existing `spec_content` is left unchanged — the same outcome as any other failed resolution

#### Scenario: Clearing the spec source
- **WHEN** a user sets `spec_source` to `none`
- **THEN** `spec_content`, `spec_url`, `spec_resolved_at`, and `spec_resolve_failed` are all cleared

### Requirement: Periodic refresh of URL-sourced specs
For every API with `spec_source` of `url`, the ingestor's poll loop SHALL periodically re-fetch `spec_url` under the same fetch-safety constraints as the initial resolution (HTTPS-only or allowlisted, non-reserved target address including through redirects, bounded response size) and overwrite `spec_content` only when the response is non-empty, within the size and nesting-depth limits, and parses as YAML-or-JSON; a failed, unsafe, or implausible fetch SHALL leave the existing `spec_content` untouched and flag the failure, without halting the ingestion pass.

#### Scenario: Successful refresh updates the snapshot
- **WHEN** a periodic refresh fetches `spec_url` under the fetch-safety constraints and the response is non-empty, within limits, and parses as YAML-or-JSON
- **THEN** `spec_content` is overwritten with the new response, `spec_resolved_at` is updated, and `spec_resolve_failed` is set to false

#### Scenario: Failed or unsafe refresh preserves the last-good snapshot
- **WHEN** a periodic refresh's fetch fails, is rejected by a fetch-safety constraint, returns an empty body, exceeds the size or nesting-depth limit, or returns a body that does not parse as YAML-or-JSON
- **THEN** `spec_content` is left unchanged, `spec_resolve_failed` is set to true, and the failure is logged without stopping the refresh pass for other APIs

#### Scenario: Refresh applies regardless of how the API entity itself was created
- **WHEN** an API has `spec_source` of `url`
- **THEN** it is refreshed on the same schedule whether the API entity is manually created or YAML-managed
