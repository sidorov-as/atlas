## ADDED Requirements

### Requirement: Flow CRUD is available through a published FlowService contract
`atlas.flows` SHALL publish Flow list/get/create/update/delete through a `FlowService` contract (following the same "published `.contracts`/`.extension_points` submodule" pattern already required of `atlas.flows` for any cross-plugin use), so other code can perform these operations without importing Flow's internal ORM models or HTTP-controller helpers directly. The existing Flow REST controllers SHALL themselves call `FlowService` rather than duplicate its logic, so the two never diverge in validation or permission checks.

#### Scenario: Existing Flow REST behavior is unchanged after the FlowService extraction
- **WHEN** `atlas.flows` is selected by a distribution after `FlowService` has been extracted
- **THEN** every `flow-management` and `visual-flow-editor` scenario passes unmodified — REST routes, response shapes, validation rules, and permission checks are identical to before the extraction

#### Scenario: Another plugin performs Flow operations through FlowService
- **WHEN** code outside `atlas.flows` (e.g. the `mcp-plugin` capability) needs to list, read, create, update, or delete a Flow
- **THEN** it does so by calling the published `FlowService` contract, not by importing `atlas_plugin_flows`'s internal models or view helpers

#### Scenario: FlowService applies the same authorization as the REST controllers
- **WHEN** `FlowService` is called to create, update, or delete a Flow by an actor who is not a member of that Flow's system's owner Group
- **THEN** the operation is rejected exactly as the existing `atlas.flows.flow.edit` permission check rejects it today
