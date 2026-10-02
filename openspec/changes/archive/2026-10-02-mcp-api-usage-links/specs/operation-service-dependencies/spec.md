## ADDED Requirements

### Requirement: A Service-to-Operation link records its origin and source
Every `ServiceOperationUsage` link SHALL record an `origin`, either `manual` or `yaml`, and a `source`, either `ui` or `mcp`. `origin` SHALL default to `manual`; `yaml` is reserved for links declared by an ingested manifest, which this capability does not yet create. `source` SHALL be set by the server from the channel of the request that created the link (the REST API used by the web UI records `ui`, the MCP API records `mcp`) and SHALL NOT be taken from the request. Both fields SHALL be visible in Django admin and SHALL NOT appear in the web UI or in existing REST responses. Links that existed before this change SHALL be given `origin` `manual` and `source` `ui`.

#### Scenario: Link created from the web UI
- **WHEN** a Service is linked to an Operation through the REST API
- **THEN** the link has `origin` `manual` and `source` `ui`

#### Scenario: Client cannot choose the source
- **WHEN** a request body includes a `source` or `origin` value
- **THEN** it is ignored or rejected, and the stored values come from the server

#### Scenario: Pre-existing links are migrated
- **WHEN** the change is applied to a database that already has `ServiceOperationUsage` rows
- **THEN** each row has `origin` `manual` and `source` `ui`

#### Scenario: Admin shows origin and source
- **WHEN** an administrator opens a link in Django admin
- **THEN** its `origin` and `source` are shown

### Requirement: A YAML-origin Service-to-Operation link cannot be removed through the API
Removing a `ServiceOperationUsage` link whose `origin` is `yaml` through the REST API or an MCP tool SHALL be rejected with a message that the link is managed by ingestion, and the link SHALL remain. Removal of one role SHALL NOT be affected by the origin of the Service's link in the other role.

#### Scenario: Unlinking a YAML-origin link over REST
- **WHEN** a user unlinks a Service from an Operation with a role whose link has origin `yaml`
- **THEN** the request is rejected as a conflict and the link remains

#### Scenario: Origin is per role
- **WHEN** a Service holds a `yaml` link as publisher and a `manual` link as subscriber on one Operation, and the subscriber link is unlinked
- **THEN** the subscriber link is removed and the publisher link remains
