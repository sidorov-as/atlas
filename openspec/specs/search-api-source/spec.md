## Purpose

API endpoints and operations as searchable documents, authorized by the endpoint and operation read permissions. Raw specifications are not indexed.

## Requirements

### Requirement: Endpoints are searchable
The APIs plugin SHALL register a search source producing one document per active endpoint, with its method and path as title and its summary and operation id as body.

#### Scenario: Found by path
- **WHEN** a user searches for part of an endpoint's path
- **THEN** the endpoint appears in results

#### Scenario: Found by operation id
- **WHEN** a user searches for an endpoint's operation id
- **THEN** the endpoint appears in results

### Requirement: Operations are searchable
The APIs plugin SHALL produce one document per active operation, with its direction and channel address as title and its summary and operation id as body.

#### Scenario: Found by channel address
- **WHEN** a user searches for part of an operation's channel address
- **THEN** the operation appears in results

### Requirement: Removed endpoints and operations are not searchable
Endpoints and operations with status removed SHALL NOT appear in results, and status changes SHALL update the index.

#### Scenario: Endpoint marked removed
- **WHEN** an endpoint becomes removed
- **THEN** it disappears from results after the next indexing run

#### Scenario: Endpoint restored
- **WHEN** a removed endpoint becomes active again
- **THEN** it reappears in results after the next indexing run

### Requirement: Hits identify the owning API and open the right page
Each result SHALL display its owning API's name or title from live data and link to the endpoint or operation within that API's page.

#### Scenario: API renamed
- **WHEN** an owning API is renamed
- **THEN** results show the new name without requiring a reindex

#### Scenario: Open an endpoint from search
- **WHEN** the user opens an endpoint result
- **THEN** the application navigates to that endpoint in its API

### Requirement: Results follow existing endpoint read rules
`resolve` SHALL apply the plugin's existing endpoint and operation read permission checks for the requesting actor.

#### Scenario: Actor lacks endpoint read permission
- **WHEN** the actor lacks permission to read an endpoint
- **THEN** it is omitted from results

### Requirement: Raw specifications are not indexed
Stored specification documents SHALL NOT be indexed.

#### Scenario: Text present only in a raw specification
- **WHEN** a user searches for text that appears only in a stored OpenAPI or AsyncAPI document
- **THEN** no result is produced for it
