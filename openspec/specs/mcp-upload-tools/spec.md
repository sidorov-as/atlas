## Purpose

MCP tools that let an agent attach large files to catalog entities: `request_attach` issues an upload ticket and returns a ready-to-use link, and `set_resource_schema` writes a Resource database schema inline when a link is not needed.

## Requirements

### Requirement: request_attach returns an upload link for a target
The MCP API SHALL publish a `request_attach` operation that takes an entity reference (`kind:name`), a field, and any target parameters, and returns an upload ticket. The MCP server SHALL present the result to the agent as a complete URL built from its configured Atlas base URL, together with the expiry, the size limit, and a ready-to-run example upload command.

#### Scenario: Agent receives a complete URL
- **WHEN** an agent calls `request_attach` for `api:booking` and field `spec`
- **THEN** the result contains a full upload URL starting with the configured Atlas base URL

#### Scenario: Entity addressed by reference
- **WHEN** an agent calls `request_attach` with a `kind:name` reference
- **THEN** the reference is resolved and no UUID lookup is needed

#### Scenario: Requires the target's write scope
- **WHEN** a PAT without the write scope that governs the target calls `request_attach`
- **THEN** the call is rejected

#### Scenario: Target plugin absent
- **WHEN** the distribution does not select the plugin that registers the requested target
- **THEN** the call is rejected as an unknown target

### Requirement: set_resource_schema writes a schema inline
The MCP API SHALL publish a `set_resource_schema` operation, available only when `atlas.database-schema` is installed, that takes a Resource reference, a dialect, and the SQL text, creates or replaces the schema, and returns the same summary as the upload path, including `parse_status` and, on failure, `parse_error`. It SHALL support `dryRun` like other authoring writes.

#### Scenario: Inline schema saved
- **WHEN** an agent calls `set_resource_schema` with a valid DDL
- **THEN** the schema is saved and the result reports `parse_status` ok

#### Scenario: Unparseable SQL is saved with the reason
- **WHEN** an agent calls `set_resource_schema` with text that has no CREATE TABLE statement
- **THEN** the SQL is saved, `parse_status` is failed, and `parse_error` contains the parser's message

#### Scenario: Dry-run saves nothing
- **WHEN** an agent calls `set_resource_schema` with `dryRun` true
- **THEN** nothing is persisted and the result is marked as a dry-run

#### Scenario: Absent when the plugin is not installed
- **WHEN** the distribution does not select `atlas.database-schema`
- **THEN** the MCP OpenAPI document contains no `set_resource_schema` operation

### Requirement: Inline content remains available and the agent chooses
Passing spec text inline (`spec_content`) and schema text inline (`set_resource_schema`) SHALL remain supported. The server instructions SHALL tell the agent to use an upload link when it can run shell commands and the content is large or already a file, to use inline content for small content or when it cannot run commands, and to ask the user to upload when neither is possible.

#### Scenario: Instructions describe both paths
- **WHEN** a client reads the server instructions of a distribution with atlas.apis installed
- **THEN** they describe when to use `request_attach` and when to use inline content

#### Scenario: Inline spec still works
- **WHEN** an agent creates an API with `spec_content`
- **THEN** the spec is stored as before

### Requirement: The upload result reports validation outcomes the agent can act on
The tool descriptions and instructions SHALL state that a schema upload's `ok` means "saved", that `parse_status` and `parse_error` describe parsing, and that a rejected upload may be retried against the same URL until it expires.

#### Scenario: Agent can distinguish saved from parsed
- **WHEN** an agent reads the `request_attach` and `set_resource_schema` descriptions
- **THEN** they explain the difference between saved and parsed
