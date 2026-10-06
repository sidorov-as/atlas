## ADDED Requirements

### Requirement: Schema writes share one function and report the parse failure reason
The plugin SHALL apply a schema write (dialect and SQL) through one shared function used by the manual CRUD endpoint, the ingestion facet writer, the MCP schema write, and the upload adapter. The function SHALL save the SQL unconditionally, set `parse_status`, and return the parser's message when parsing fails. The message SHALL be exposed to callers as `parse_error` and SHALL be empty when parsing succeeds.

#### Scenario: Failed parse returns the reason
- **WHEN** a schema is written with SQL that contains no CREATE TABLE statement
- **THEN** the SQL is saved, `parse_status` is failed, and `parse_error` is "No CREATE TABLE statement found"

#### Scenario: Successful parse has no error
- **WHEN** a schema is written with valid DDL
- **THEN** `parse_status` is ok and `parse_error` is empty

#### Scenario: All write paths behave alike
- **WHEN** the same SQL is written through the CRUD endpoint, ingestion, the MCP schema write, and an upload
- **THEN** each stores the same `parsed_schema` and `parse_status`

### Requirement: Schema writes enforce write permission on every path
The shared write path SHALL reject a write to a YAML-managed Resource and SHALL require the caller to hold the Resource's edit permission, regardless of whether the call arrives through the session-authenticated CRUD endpoint, the MCP API with a PAT, or an upload ticket.

#### Scenario: YAML-managed Resource through MCP
- **WHEN** an MCP schema write targets a YAML-managed Resource
- **THEN** it is rejected as read-only

#### Scenario: Caller outside the owner group
- **WHEN** a PAT whose owner may not edit the Resource attempts a schema write
- **THEN** it is rejected

### Requirement: Database Schema is an upload target
The plugin SHALL register `(resource, schema)` as an upload target. The ticket parameters SHALL include the SQL dialect, validated at request time. The adapter SHALL create the Facet if absent, replace it otherwise, and return a summary containing `parse_status`, `parse_error`, and the number of tables found.

#### Scenario: Upload creates the facet
- **WHEN** a client uploads DDL to a schema ticket for a Resource without a Database Schema facet
- **THEN** the facet is created with the ticket's dialect and the summary reports the table count

#### Scenario: Upload replaces an existing facet
- **WHEN** a client uploads DDL to a schema ticket for a Resource that already has a facet
- **THEN** the SQL, dialect, and parsed schema are replaced

#### Scenario: Unparseable upload is saved and reported
- **WHEN** a client uploads text that cannot be parsed
- **THEN** the response has `ok` true with `parse_status` failed and the `parse_error` message
