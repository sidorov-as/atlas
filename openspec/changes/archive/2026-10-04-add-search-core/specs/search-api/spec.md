## ADDED Requirements

### Requirement: Search endpoint
The search plugin SHALL provide an authenticated endpoint that accepts a text query, an optional list of kinds, a page and a page size, and returns ranked results. Each result SHALL include its document id, kind, title, a link target, an optional snippet, and a display label for its kind. The response shape SHALL NOT depend on the selected engine.

#### Scenario: Basic query
- **WHEN** an authenticated user searches for text matching several documents
- **THEN** the response lists matching results ordered by relevance with the specified fields

#### Scenario: Filter by kind
- **WHEN** the request lists specific kinds
- **THEN** only results of those kinds are returned

#### Scenario: Empty or too-short query
- **WHEN** the query is empty or below the minimum length
- **THEN** the endpoint returns an empty result set without querying the engine

#### Scenario: Unauthenticated request
- **WHEN** an unauthenticated client calls the endpoint
- **THEN** access is denied as for other API endpoints

### Requirement: Results are authorized by the owning source
Every result SHALL come from the owning source's `resolve` for the requesting actor. The system SHALL NOT return data taken from the index for a document the actor cannot read, nor reveal its existence through titles, snippets or counts.

#### Scenario: Unreadable document is never returned
- **WHEN** a candidate document is not readable by the actor
- **THEN** it is absent from results and does not contribute to the reported total

#### Scenario: Deleted document still in the index
- **WHEN** the index still holds a document whose live object was deleted
- **THEN** it is omitted from results

#### Scenario: Pages stay full where possible
- **WHEN** some candidates are filtered out by authorization
- **THEN** the system fetches additional candidates to fill the page when more exist

### Requirement: Snippets are consistent across engines
The system SHALL provide a snippet for a result from the resolved hit's text around the first query match, unless the engine declares it supplies highlights, in which case the engine's highlights SHALL be used. Snippet text SHALL be returned in a form that cannot inject markup.

#### Scenario: Core-generated snippet
- **WHEN** the engine does not supply highlights and the body contains the query
- **THEN** the result includes a snippet around the match with the match marked

#### Scenario: Match only in title
- **WHEN** the match is in the title and not in the body
- **THEN** the result's snippet falls back to the summary or beginning of the body

#### Scenario: Markup in indexed text
- **WHEN** the body contains HTML or markdown markup
- **THEN** the snippet carries no executable markup

### Requirement: Status endpoint
The search plugin SHALL provide an endpoint reporting engine health and indexing state, available to authenticated users with limited detail and to administrators with full detail.

#### Scenario: Engine unreachable
- **WHEN** the engine health check fails
- **THEN** status reports unhealthy and search requests return a clear service-unavailable response instead of an empty result

#### Scenario: Non-administrator sees limited detail
- **WHEN** a non-administrator reads status
- **THEN** operational error text and internal identifiers are omitted
