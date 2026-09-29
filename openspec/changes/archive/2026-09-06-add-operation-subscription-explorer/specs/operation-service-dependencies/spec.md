## ADDED Requirements

### Requirement: Service-to-Operation usage is an explicit, plugin-owned link with a role
A Service's relationship to a specific Operation SHALL be recorded as an explicit `ServiceOperationUsage` link (service, operation, role, created-at, created-by), created and removed through dedicated endpoints rather than through the generic derived entity-relations system. `role` SHALL be either `publisher` or `subscriber`, asserted independently of the Operation's own `direction`.

#### Scenario: A service can be linked as a subscriber
- **WHEN** a Service with no prior link to an Operation is linked to it with `role=subscriber`
- **THEN** a `ServiceOperationUsage` row is created recording that Service, Operation, and role, with the acting user and timestamp

#### Scenario: A service can be linked as a publisher
- **WHEN** a Service with no prior link to an Operation is linked to it with `role=publisher`
- **THEN** a `ServiceOperationUsage` row is created recording that role, independent of the Operation's own `direction`

#### Scenario: Multiple services can hold the same role on one operation
- **WHEN** two different Services are each linked to the same Operation with `role=subscriber`
- **THEN** both links succeed, since more than one subscriber to the same channel is a valid, ordinary shape

#### Scenario: A service cannot be linked to the same operation with the same role twice
- **WHEN** a Service that already has a `ServiceOperationUsage` link to an Operation with a given role is linked to that same Operation with the same role again
- **THEN** the request is rejected rather than creating a duplicate link

#### Scenario: A service can hold both roles on the same operation
- **WHEN** a Service is linked to an Operation as `publisher` and separately as `subscriber`
- **THEN** both links succeed as two distinct `ServiceOperationUsage` rows

#### Scenario: Unlinking targets exactly one role
- **WHEN** a Service holding both `publisher` and `subscriber` links to an Operation is unlinked with a specific `role`
- **THEN** only the `ServiceOperationUsage` row for that role is removed, and the other role's link remains

#### Scenario: Role is not validated against the operation's direction
- **WHEN** a Service is linked to an Operation with a `role` that would be unusual given the Operation's `direction` (e.g. a second `publisher` on a `send` operation whose document owner is already the implied publisher)
- **THEN** the link is still created — `role` is asserted independently of `direction` and is not constrained by it in this change

### Requirement: The API document's own owning Service is never self-linked
The Service found via an Operation's API's `apiProvidedBy` relation SHALL NOT be recorded as a `ServiceOperationUsage` row for that Operation; its role SHALL instead be derived automatically from the Operation's `direction` (`send` implies publisher, `receive` implies subscriber) wherever that Operation's roles are displayed.

#### Scenario: Linking the document owner is rejected
- **WHEN** a request attempts to link an Operation's own `apiProvidedBy` Service to that Operation via `ServiceOperationUsage`
- **THEN** the request is rejected, since that Service's role is already implied by the Operation's `direction`

#### Scenario: The document owner's implied role appears in listings without a link row
- **WHEN** an Operation's publishers/subscribers are listed or graphed
- **THEN** its `apiProvidedBy` Service appears with its direction-implied role even though no `ServiceOperationUsage` row exists for it

### Requirement: Linked Services are searchable, filterable, and sortable
An Operation's Linked Services listing SHALL support searching by service name/display name, filtering by team and by role, and sorting by service name or team name (ascending/descending), with this state reflected in the URL.

#### Scenario: Search by service name
- **WHEN** a user searches Linked Services for a substring of a service's display name, case-insensitively
- **THEN** only matching services are shown

#### Scenario: Filter by role
- **WHEN** a user filters Linked Services to `role=publisher`
- **THEN** only Services linked with that role are shown

#### Scenario: Filter by team
- **WHEN** a user filters Linked Services to a specific team
- **THEN** only services on that team are shown

#### Scenario: Search and filter state is shareable via URL
- **WHEN** a user searches and filters the Linked Services tab and shares the resulting URL
- **THEN** opening that URL reproduces the same search text, role filter, team filter, and sort order

### Requirement: Linking and unlinking are permission-gated and hidden, not just disabled
The Link Service action and each row's Unlink action SHALL be visible only to a user holding `operationDependency.create` / `operationDependency.delete` respectively; a user without the permission SHALL NOT see the action at all.

#### Scenario: Read-only user sees no Link/Unlink actions
- **WHEN** a user without `operationDependency.create` or `operationDependency.delete` views an Operation's Linked Services tab
- **THEN** no "Link service" button and no per-row "Unlink" action are rendered

### Requirement: Publishers & subscribers graph is scoped to the shared channel, not one Operation row
An Operation's Overview tab SHALL show a read-only graph aggregating every `Operation` (including ones belonging to other API documents) that shares its `channel_address`, showing each aggregated Operation's linked Services (including each Operation's document-owner role implied by `direction`) as publisher or subscriber nodes, supporting pan, zoom, and fit-to-view, with no drag-repositioning, connection-creation, or deletion available.

#### Scenario: Two operations on the same channel from different APIs share one graph
- **WHEN** Operation A (on API X, `direction=send`) and Operation B (on API Y, `direction=receive`) share the same `channel_address`
- **THEN** viewing either Operation's Overview shows one graph containing both APIs' implied/linked roles for that channel, not two separate single-sided graphs

#### Scenario: Publisher and subscriber nodes are visually distinguished
- **WHEN** the publishers/subscribers graph is rendered
- **THEN** publisher nodes and subscriber nodes are visually distinguishable by a label, not by color alone

#### Scenario: Clicking a Service node navigates to that Service
- **WHEN** a user clicks a Service node in the publishers/subscribers graph
- **THEN** the user is navigated to that Service's detail page

#### Scenario: Graph nodes cannot be edited
- **WHEN** a user attempts to drag a node, or draw or delete a connection, in the publishers/subscribers graph
- **THEN** no change occurs — the graph is display-only

#### Scenario: Empty graph shows a call to action instead of a blank canvas
- **WHEN** a channel has no linked Services and no document-owner-implied roles beyond the current Operation's own
- **THEN** its Overview shows an explanatory empty state with a "Link service" action, not an empty graph canvas

#### Scenario: Large participant counts are capped on the compact graph
- **WHEN** a channel's aggregated publishers and subscribers exceed 12 nodes
- **THEN** the compact Overview graph shows at most 12 nodes plus an indicator of how many more exist, rather than rendering all of them

### Requirement: Cross-API aggregation respects each aggregated API's visibility
The channel-scoped publishers/subscribers graph and the `/consumers` aggregation SHALL exclude any aggregated `Operation` whose own `API` is not visible to the requesting principal, and SHALL do so without revealing that a hidden Operation exists (no count, placeholder node, or error naming it).

**Implementation note (verified, task 3.4):** no per-entity `API` visibility mechanism exists anywhere in this catalog — `openspec/specs/catalog-auth/spec.md` makes unrestricted read for any authenticated user an explicit requirement (v1 has no per-entity read ACL). This requirement is therefore currently unenforceable and unimplemented by design (user decision 2026-09-06, see `design.md` Decision 7); the scenarios below describe intended behavior for if/when a real visibility mechanism is introduced, not current behavior.

#### Scenario: A restricted API's operation is excluded from another API's public graph
- **WHEN** a public `API`'s Operation and a restricted-visibility `API`'s Operation share the same `channel_address`, and a viewer without access to the restricted API views the public Operation's graph
- **THEN** the restricted API's Operation, its linked Services, and its document-owner implied role are all absent from the graph and from any node count shown, with no indication that a hidden participant exists

#### Scenario: A viewer with access to both APIs sees the full aggregation
- **WHEN** a viewer has read access to every `API` contributing an Operation to a shared `channel_address`
- **THEN** the graph and `/consumers` response include all of them, unaffected by the filter above

### Requirement: Linked Services reflects a removed operation's status
An Operation's Linked Services tab SHALL show a visible warning when the Operation itself has been removed (`status=removed`), rather than presenting its existing links as if the operation were still active.

#### Scenario: Linked Services warns for a removed operation
- **WHEN** a `removed` Operation's Linked Services tab is viewed and it still has linked Services
- **THEN** the tab displays a warning that the operation no longer exists in the API alongside the (still-listed) Services that depend on it

### Requirement: Graph failures do not block operation documentation
A failure loading the publishers/subscribers graph or the Linked Services list SHALL show an inline retry affordance in that section only, and SHALL NOT prevent the rest of the Operation page (Overview documentation, Message tab) from rendering.

#### Scenario: Graph load failure is isolated
- **WHEN** the publishers/subscribers graph data request fails
- **THEN** the graph section shows an inline error with a retry action while the operation's documentation sections render normally
