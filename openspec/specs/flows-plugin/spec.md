## Purpose

Flow (hand-authored, ordered cross-system process documentation) is provided entirely by the optional `atlas.flows` plugin, extracted out of core so a distribution can omit it. It declares a manifest dependency on Standard Catalog (a Flow's `system` field resolves a System entity), enforces its own ownership-scoped write permission through the published policy-evaluator contract rather than core-internal permission checks, and depends on no other optional plugin — matching the shape of `atlas.apis`/`atlas.c4`/`atlas.standard-catalog`.

## Requirements

### Requirement: Flow is an optional plugin-provided feature
Flow (hand-authored, ordered cross-system process documentation) SHALL be provided entirely by the `atlas.flows` plugin; a distribution MAY omit it.

#### Scenario: Distribution without atlas.flows composes successfully
- **WHEN** a distribution selects `atlas.standard-catalog` but not `atlas.flows`
- **THEN** composition succeeds, and no `/flows` routes or nav entry are present

#### Scenario: Distribution with atlas.flows behaves exactly as before extraction
- **WHEN** a distribution selects `atlas.flows`
- **THEN** every `flow-management` and `visual-flow-editor` scenario passes unmodified — REST routes, response shapes, validation rules, and canvas rendering are unchanged from before this plugin existed

### Requirement: Flows plugin declares a manifest dependency on Standard Catalog
`atlas.flows` SHALL declare a manifest dependency on `atlas.standard-catalog` within a compatible version range; composition SHALL fail if that dependency isn't satisfied.

#### Scenario: Compatible Standard Catalog satisfies the dependency
- **WHEN** a distribution selects `atlas.flows` and a version of `atlas.standard-catalog` within its declared compatible range
- **THEN** composition succeeds

#### Scenario: Missing Standard Catalog fails composition
- **WHEN** a distribution selects `atlas.flows` without selecting `atlas.standard-catalog`
- **THEN** composition fails, identifying the unsatisfied dependency

### Requirement: Flow writes require a registered, ownership-scoped permission
Creating, updating, or deleting a Flow SHALL require the `atlas.flows.flow.edit` permission, evaluated by the deployment's configured policy evaluator against the Flow's `system` as the resource — granted only to a member of that system's owner Group (or a superuser). Reading a Flow SHALL require only the `atlas.flows.flow.read` permission, granted to any authenticated principal.

#### Scenario: Non-member cannot create a Flow under a system they don't own
- **WHEN** an authenticated user who is not a member of a System's owner Group attempts to create a Flow under that System
- **THEN** the request is rejected

#### Scenario: Member can create, edit, and delete a Flow under their system
- **WHEN** an authenticated user who is a member of a System's owner Group creates, updates, or deletes a Flow under that System
- **THEN** the request succeeds

#### Scenario: Any authenticated user can read a Flow
- **WHEN** any authenticated user requests a Flow's list or detail endpoint
- **THEN** the request succeeds regardless of System ownership

### Requirement: No core module depends on Flow, and Flow depends on no other optional plugin
Nothing outside `atlas.flows` SHALL import Flow-specific code, and `atlas.flows` SHALL NOT import another optional plugin's implementation directly (only `atlas_plugin_api` and other plugins' declared `.contracts`/`.extension_points` submodules).

#### Scenario: Import-boundary check passes for atlas.flows
- **WHEN** the plugin import-boundary check runs against `atlas_plugin_flows`
- **THEN** it finds no import of a `server.apps.catalog`/`server.apps.plugins` module outside the published `atlas_plugin_api` contract surface, and no import of another plugin's implementation module

#### Scenario: Core contains no Flow-specific code
- **WHEN** `server.apps.catalog` and the frontend `atlas.core` plugin module are inspected after this change
- **THEN** neither contains a `Flow` model, Flow REST controller, or Flow page/component

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
