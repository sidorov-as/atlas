## ADDED Requirements

### Requirement: The MCP API publishes upload ticket requests
The curated MCP API SHALL publish the `request_attach` operation. It SHALL be present whenever at least one upload target is registered by an installed plugin and absent otherwise. It SHALL be authenticated by a Personal Access Token and SHALL require the write scope that governs the requested target.

#### Scenario: Present with a registered target
- **WHEN** the distribution selects `atlas.apis`
- **THEN** the MCP OpenAPI document contains `request_attach`

#### Scenario: Absent without any target
- **WHEN** no installed plugin registers an upload target
- **THEN** the MCP OpenAPI document contains no `request_attach` operation

### Requirement: The upload endpoint is outside the MCP API's PAT requirement
The ticket upload `PUT` SHALL NOT be part of the MCP OpenAPI document and SHALL NOT be exposed as an MCP tool, because it is intended to be called by the agent's shell, not through MCP. Its only credential SHALL be the ticket token.

#### Scenario: No tool for the upload itself
- **WHEN** a client lists the MCP tools
- **THEN** there is no tool that performs the raw upload
