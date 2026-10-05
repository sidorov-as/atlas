# search-postgres-engine Specification

## Purpose
A search engine adapter that keeps the index in the application's PostgreSQL database.

## Requirements

### Requirement: Postgres adapter requires no extra infrastructure
The Postgres engine plugin SHALL implement the engine contract using the application's existing PostgreSQL database, and SHALL add no service to the deployment.

#### Scenario: Default deployment
- **WHEN** a distribution selects the search plugin and the Postgres engine plugin
- **THEN** search works with no additional service configured

### Requirement: Relevance-ranked full-text matching
The adapter SHALL match query terms against title and body using PostgreSQL full-text search, rank title matches above body-only matches, and return ordered candidate ids with scores.

#### Scenario: Title outranks body
- **WHEN** one document has the term in its title and another only in its body
- **THEN** the title match is ranked first

#### Scenario: Multiple terms
- **WHEN** a query contains several words
- **THEN** only documents containing all of them match

#### Scenario: Index-backed query
- **WHEN** a query runs
- **THEN** it uses an index rather than scanning every document

### Requirement: Atomic replace
The adapter SHALL implement replace-all so that readers see either the old or the new index, never a partial one.

#### Scenario: Rebuild during queries
- **WHEN** a rebuild runs while queries arrive
- **THEN** each query sees a complete index

### Requirement: Conformance
The adapter SHALL pass the shared engine conformance suite.

#### Scenario: Suite passes
- **WHEN** the conformance suite runs against the adapter
- **THEN** all checks pass

### Requirement: Safe handling of user text
The adapter SHALL treat the user's query as data, not as query syntax that can raise errors or change behaviour.

#### Scenario: Query with operators or quotes
- **WHEN** a query contains characters meaningful in full-text query syntax
- **THEN** the query executes without error and treats them as plain text
