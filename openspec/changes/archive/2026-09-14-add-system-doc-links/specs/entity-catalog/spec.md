## ADDED Requirements

### Requirement: Metadata links include resource descriptions
Every catalog entity's `metadata.links[]` item SHALL expose `url`, `title`,
`description`, and `type`. `url` SHALL be non-empty; `title`, `description`,
and `type` SHALL default to empty strings so existing manifests and API clients
that omit them remain valid.

#### Scenario: Existing link remains valid without a description
- **WHEN** an entity is created or ingested with a link containing only `url`,
  `title`, and `type`
- **THEN** it is accepted and retrieved with an empty `description`

### Requirement: System document links have a paginated read API
The catalog API SHALL expose `GET /api/systems/{id}/docs/` to authenticated
readers. The endpoint SHALL return that System's metadata links in the standard
paginated envelope and SHALL support `q`, `page`, and `page_size` query
parameters. `q` SHALL match title or description case-insensitively, and the
response order SHALL retain the System's declared link order after filtering.

#### Scenario: Search filters System document links
- **WHEN** a reader requests a System's document links with `q=dashboard`
- **THEN** the response contains only links whose title or description matches
  `dashboard` case-insensitively

#### Scenario: Document links are paginated
- **WHEN** a System has more document links than the requested `page_size`
- **THEN** the response contains the requested page and the total item count
  and page metadata

#### Scenario: Document-link API is read-only
- **WHEN** a client sends a non-GET request to a System's document-links URL
- **THEN** the request is rejected and no System metadata changes

#### Scenario: Manual Docs management uses the System PATCH API
- **WHEN** an authorized owner adds, edits, or removes a document link in the
  System Docs tab
- **THEN** the client updates the complete `metadata.links` list through the
  existing System PATCH route, while the document-links URL remains read-only

#### Scenario: Missing System has no document-link listing
- **WHEN** a reader requests document links for a nonexistent System id
- **THEN** the API returns the same not-found result as System retrieval
