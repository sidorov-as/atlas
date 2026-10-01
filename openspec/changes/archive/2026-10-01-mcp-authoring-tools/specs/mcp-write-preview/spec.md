## ADDED Requirements

### Requirement: Authoring writes support dry-run
`create_entity`, `update_entity`, `create_flow`, `update_flow`, `create_relationship`, `update_relationship`, and `delete_relationship` SHALL accept a `dryRun` flag. When it is true, the operation SHALL run the same authorization, validation, and reference resolution as a real write, SHALL persist nothing, and SHALL return an envelope marked `dryRun: true` containing the resulting state and a list of field-level changes.

#### Scenario: Dry-run create persists nothing
- **WHEN** a client calls `create_entity` with `dryRun` true and a valid body
- **THEN** the response reports the entity that would be created, and no entity, relation, or audit record exists afterward

#### Scenario: Dry-run update reports before and after
- **WHEN** a client calls `update_entity` with `dryRun` true and a changed description
- **THEN** the response lists the changed field with its current and proposed values, and the stored entity is unchanged

#### Scenario: Dry-run reports the same errors as a real write
- **WHEN** a dry-run body would be rejected by validation, reference resolution, or RBAC
- **THEN** the dry-run is rejected with the same error a real write would produce

#### Scenario: Dry-run still requires the write scope
- **WHEN** a request authenticated by a PAT without the matching write scope calls an operation with `dryRun` true
- **THEN** the request is rejected

#### Scenario: Real writes keep their existing response shape
- **WHEN** a client calls a write operation without `dryRun`
- **THEN** the response has the same shape as before this capability

### Requirement: Dry-run performs no external side effects
A dry-run SHALL NOT fetch a spec URL or trigger any other effect outside the database transaction. When a real write would perform such an effect, the dry-run response SHALL include a warning saying so.

#### Scenario: Spec URL is not fetched in a dry-run
- **WHEN** a client calls `create_entity` for an API with `specSource` `url` and `dryRun` true
- **THEN** no outbound request is made and the response warns that the URL would be fetched on a real write

### Requirement: validate_flow checks a flow body without saving
The MCP API SHALL publish a `validate_flow` operation, available only when `atlas.flows` is installed, that takes a flow body (and optionally an existing flow id) and reports every violation of the flow rules without saving: unresolvable step `entity_ref`, duplicate step ids, transitions to missing steps, cycles, a step carrying more than one of `entity_ref`, `external_label`, `query_ref`, and `event_ref`, a `flow_ref` or `link_url` step carrying any other reference field, and exceeded size limits (description, documentation, step count). It SHALL return all violations found, not only the first.

#### Scenario: Valid flow
- **WHEN** a client calls `validate_flow` with a flow that satisfies every rule
- **THEN** the response reports it valid and nothing is saved

#### Scenario: Multiple violations are reported together
- **WHEN** a flow contains a duplicate step id and a transition to a missing step
- **THEN** the response lists both violations

#### Scenario: Cycle is reported
- **WHEN** a flow's transitions form a cycle
- **THEN** the response reports the cycle and the step ids involved

#### Scenario: Absent when atlas.flows is not installed
- **WHEN** the distribution does not select `atlas.flows`
- **THEN** the MCP OpenAPI document contains no `validate_flow` operation

#### Scenario: validate_flow requires the flows read scope
- **WHEN** a request authenticated by a PAT without `flows:read` calls `validate_flow`
- **THEN** it is rejected
