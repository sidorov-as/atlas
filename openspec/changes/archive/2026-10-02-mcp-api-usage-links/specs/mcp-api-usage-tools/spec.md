## ADDED Requirements

### Requirement: Usage link tools manage Service-to-Endpoint and Service-to-Operation links in batches
The MCP API SHALL publish four write tools: `link_endpoint_consumers`, `unlink_endpoint_consumers`, `link_operation_participants`, and `unlink_operation_participants`. Each SHALL take one Service ref (a Component) and a non-empty list of items, and SHALL apply the whole list in one call. An endpoint item identifies an Endpoint; an operation item identifies an Operation and carries a `role` of `publisher` or `subscriber`. The tools SHALL create and remove the same explicit `ServiceEndpointUsage` and `ServiceOperationUsage` links the REST API manages, and SHALL apply the same rules as the REST endpoints, including permission checks on the Service, the rejection of a removed Endpoint, and the rejection of linking an Operation's own document-owning Service.

#### Scenario: Linking several endpoints to a Service in one call
- **WHEN** an authorized client calls `link_endpoint_consumers` for `component:booking-web` with three items naming three Endpoints
- **THEN** a `ServiceEndpointUsage` link exists for each, and the response reports each item's outcome

#### Scenario: Linking an operation requires a role
- **WHEN** a client calls `link_operation_participants` with an item that has no `role`
- **THEN** that request is rejected and nothing is linked

#### Scenario: A Service may hold both roles on one operation
- **WHEN** a client links the same Service to the same Operation once as `publisher` and once as `subscriber`
- **THEN** two distinct links exist, and unlinking one role leaves the other

#### Scenario: A non-Component is rejected as the Service
- **WHEN** a client passes a ref that resolves to a System, an API, or a Resource as the Service
- **THEN** the request is rejected and nothing is linked

#### Scenario: Missing permission on the Service is rejected
- **WHEN** the acting user lacks the dependency create (or delete) permission on the Service
- **THEN** the request is rejected the same way the REST endpoint rejects it, and nothing changes

### Requirement: An item identifies its endpoint or operation by id or by natural key
Every item SHALL identify its target in exactly one of two forms. The id form is `endpoint_id` for an Endpoint or `operation_id` for an Operation. The natural-key form is `{api, method, path}` for an Endpoint, with `api` an API ref, and `{api, channel_address, direction}` for an Operation. An item that gives both forms, or neither, or a partial natural key, SHALL be rejected as invalid for that item without affecting the others. An Endpoint's natural key identifies at most one Endpoint of the API, whatever its status. An Operation's natural key SHALL match only active (not removed) Operations of the API, and MAY match more than one.

#### Scenario: Endpoint addressed by natural key
- **WHEN** an item is `{api: "api:booking", method: "GET", path: "/bookings/{id}"}` and that API has one active Endpoint with that method and path
- **THEN** the item resolves to that Endpoint

#### Scenario: Both forms given
- **WHEN** an item carries both an `endpoint_id` and an `{api, method, path}`
- **THEN** that item is reported as invalid and the other items are processed

#### Scenario: Natural key that matches nothing
- **WHEN** an item's natural key matches no active Endpoint of that API
- **THEN** that item is reported `not_found`, with the API and key it looked for, and nothing is created for it

#### Scenario: Operation key that matches more than one operation
- **WHEN** an operation item's `{api, channel_address, direction}` matches more than one active Operation of that API
- **THEN** that item is reported `ambiguous` with the candidate operation ids, and nothing is created or removed for it

#### Scenario: Operation key ignores removed operations
- **WHEN** an API has a removed Operation and one active Operation with the same channel and direction
- **THEN** the key resolves to the active one

#### Scenario: Natural key of a removed endpoint
- **WHEN** a link item's `{api, method, path}` identifies an Endpoint that has been removed
- **THEN** that item is reported `conflict`, the same as linking it by id

### Requirement: A batch succeeds partially with a status for every item
Each tool SHALL process every item independently and SHALL return one result per item, in request order, each with a `status`. Link tools SHALL use `created`, `unchanged` (the link already existed), `not_found`, `ambiguous`, `conflict`, and `invalid`. Unlink tools SHALL use `removed`, `unchanged` (there was no such link), `not_found`, `ambiguous`, `conflict`, and `invalid`. A failing item SHALL NOT prevent or undo any other item. The response SHALL also state the count of items per status. Request-level problems (an unresolvable Service, a missing scope, a batch over the size limit) SHALL reject the whole request and change nothing.

#### Scenario: One stale item does not fail the batch
- **WHEN** a batch of 50 endpoint links contains one item whose Endpoint no longer exists
- **THEN** 49 links are created or reported unchanged, and that one item is reported `not_found`

#### Scenario: Re-running a batch is idempotent
- **WHEN** the same link batch is sent a second time
- **THEN** every item that succeeded before is reported `unchanged` and no duplicate link is created

#### Scenario: Linking an operation's own document owner
- **WHEN** an operation item names the Service that is the API document's own owner
- **THEN** that item is reported `conflict` with a message that its role is implied by the operation's direction

#### Scenario: Linking to a removed endpoint by id
- **WHEN** an item names a removed Endpoint by `endpoint_id`
- **THEN** that item is reported `conflict` and nothing is created for it

#### Scenario: Unlinking a link that does not exist
- **WHEN** an unlink item names a target the Service is not linked to
- **THEN** that item is reported `unchanged`

#### Scenario: Unlinking from a removed endpoint is allowed
- **WHEN** an unlink item names a removed Endpoint the Service is linked to
- **THEN** the link is removed and the item is reported `removed`

#### Scenario: Oversized batch is rejected whole
- **WHEN** a request carries more items than the batch limit
- **THEN** the request is rejected and no item is processed

### Requirement: Usage link writes support dryRun
Every usage link tool SHALL accept `dryRun`. With `dryRun` true, nothing SHALL be saved, and the response SHALL report the per-item statuses and counts the real call would produce, flagged as a preview.

#### Scenario: Dry-run previews a batch
- **WHEN** `link_endpoint_consumers` is called with `dryRun` true and a batch where two links already exist and three are new
- **THEN** the response reports two `unchanged` and three `created`, and no link exists afterwards that did not exist before

#### Scenario: Dry-run of an unlink
- **WHEN** `unlink_operation_participants` is called with `dryRun` true
- **THEN** the response lists the links that would be removed and every link remains

### Requirement: Linking an endpoint reports the consumesAPI side effect
`link_endpoint_consumers` SHALL, as the REST link does, ensure the Service's `consumesAPI` includes the Endpoint's API, and SHALL report in each item's result whether that API relation was added by that item. `link_operation_participants` SHALL NOT change the Service's `consumesAPI`, `providesApis`, or any other relation. The unlink tools SHALL NOT remove any `consumesAPI`.

#### Scenario: consumesAPI added by the first link to an API
- **WHEN** a Service that does not consume an API is linked to one of its Endpoints
- **THEN** the item is `created` and reports that `consumesAPI` was added

#### Scenario: Second endpoint of the same API
- **WHEN** the same Service is then linked to another Endpoint of that API
- **THEN** the item is `created` and reports that no `consumesAPI` was added

#### Scenario: Operation links leave the Service's relations alone
- **WHEN** a Service is linked to an Operation
- **THEN** the Service's `consumesAPI` and `providesApis` are unchanged

#### Scenario: Dry-run reports the side effect without applying it
- **WHEN** a link batch runs with `dryRun` true
- **THEN** the items report which `consumesAPI` relations would be added, and none is added

### Requirement: Usage link tools require the apis:write scope
All four usage link tools SHALL require the `apis:write` PAT scope, checked before the owning user's own permissions. The scope narrows the user's permissions and SHALL NOT grant one the user lacks.

#### Scenario: Token without the scope is rejected
- **WHEN** a request authenticated by a PAT scoped to `catalog:write` but not `apis:write` calls `link_endpoint_consumers`
- **THEN** the request is rejected and nothing is linked

#### Scenario: Token with the scope cannot exceed its owner
- **WHEN** a PAT with `apis:write` belongs to a user who lacks permission on the Service
- **THEN** the request is rejected

### Requirement: Links created through MCP are recorded as manual with source mcp
Every link created by a usage link tool SHALL be recorded with `origin` `manual` and `source` `mcp`, and the acting user as its creator.

#### Scenario: Link created over MCP
- **WHEN** a link is created by `link_operation_participants`
- **THEN** its `origin` is `manual`, its `source` is `mcp`, and its creator is the PAT's owning user

### Requirement: Usage link tools never remove a YAML-origin link
`unlink_endpoint_consumers` and `unlink_operation_participants` SHALL NOT remove a link whose `origin` is `yaml`; that item SHALL be reported `conflict` with a message that the link is managed by ingestion.

#### Scenario: Unlinking a YAML-origin link
- **WHEN** an unlink item targets a link with origin `yaml`
- **THEN** the item is reported `conflict`, and the link remains
