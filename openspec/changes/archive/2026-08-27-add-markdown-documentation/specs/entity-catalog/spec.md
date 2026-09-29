## MODIFIED Requirements

### Requirement: Entity envelope
Every entity SHALL have `apiVersion`, `kind`, `metadata: {name, title, description, documentation, labels, tags, links[]}`, and a kind-specific `spec`. `description` is an optional short summary and `documentation` is an optional Markdown document; both default to empty strings.

#### Scenario: Entity created with only required fields
- **WHEN** a System is created with only `metadata.name` and `spec.owner` set
- **THEN** it is stored with the remaining envelope fields, including empty `description` and `documentation`, at their defaults and is retrievable by its id

### Requirement: List filtering and search
List endpoints for ingestible kinds SHALL support `?owner=`, `?lifecycle=`, `?type=`, `?tags=` (repeatable; matches an entity carrying **any** of the given tags), `?q=` (name/description/documentation search), and `?page=`/`?page_size=` for pagination. Component, Resource, and API lists SHALL additionally support `?system=`. Responses SHALL be a paginated envelope (item count, page count, page size, and the current page's items) rather than a bare array.

#### Scenario: Filtering the Systems list by owner
- **WHEN** `GET /api/systems/?owner=group:identity-team` is called
- **THEN** only Systems owned by that Group are returned

#### Scenario: Searching the Systems list by text
- **WHEN** `GET /api/systems/?q=user` is called
- **THEN** only Systems whose name, description, or documentation contains "user" are returned

#### Scenario: Filtering a list by multiple tags matches any of them
- **WHEN** `GET /api/components/?tags=payments&tags=internal` is called
- **THEN** only Components carrying at least one of `payments` or `internal` in their tags are returned

#### Scenario: Listing entities returns a paginated envelope
- **WHEN** `GET /api/components/?page=2&page_size=10` is called
- **THEN** the response contains at most 10 Components for page 2, along with the total item count and page metadata

#### Scenario: Listing entities belonging to a System
- **WHEN** `GET /api/components/?system=system:payments` is called
- **THEN** only Components belonging to that System are returned
