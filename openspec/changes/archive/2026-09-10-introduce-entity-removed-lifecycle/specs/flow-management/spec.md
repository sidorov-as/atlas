## ADDED Requirements

### Requirement: Reading a Flow surfaces live status of entity_ref-targeted entities
When a Flow is read (list or detail), for each step carrying a non-empty `entity_ref` that resolves to a System, Component, Resource, or API, the response SHALL additionally include that entity's current `status` (`active`/`removed`) and `deprecated` flag, resolved at read time — mirroring the existing live-status surfacing already provided for `query_ref`/`event_ref` steps in the `flow-query-event-steps` capability. This SHALL NOT modify the step's stored `entity_ref`. When the referenced entity no longer resolves at all (e.g. it was purged), the read SHALL still succeed, presenting the step without a live status rather than failing the Flow read.

#### Scenario: Reading a Flow reports a removed entity's current status
- **WHEN** a Flow containing a step whose `entity_ref` resolves to a Component with `status: removed` is read
- **THEN** the response includes that step's stored `entity_ref` unchanged, plus the Component's current `status: removed`

#### Scenario: Reading a Flow reports a deprecated entity's current status
- **WHEN** a Flow containing a step whose `entity_ref` resolves to a Component with `deprecated: true` is read
- **THEN** the response includes `deprecated: true` for that step's target

#### Scenario: A removed entity_ref target does not invalidate an existing Flow's reference
- **WHEN** an entity referenced by an existing Flow step's `entity_ref` becomes `removed` after the Flow was saved
- **THEN** the Flow continues to resolve and read successfully, showing the live `removed` status rather than rejecting the read

#### Scenario: Reading a Flow whose entity_ref target no longer resolves at all does not fail the read
- **WHEN** a Flow containing a step whose `entity_ref` no longer resolves to any entity (e.g. it was purged) is read
- **THEN** the read succeeds, the step's stored `entity_ref` is presented, and no live status is included for that step

### Requirement: Flow diagram nodes visibly flag a removed or deprecated referenced entity
A step's node whose resolved reference (`entity_ref`, `query_ref`, or `event_ref`) currently carries `status: removed` or `deprecated: true` SHALL render a visible warning indicator on the node, distinguishing removed from deprecated, on both the read-only detail page and the edit page's canvas.

#### Scenario: A step referencing a removed entity shows a warning indicator
- **WHEN** a Flow's diagram renders a step whose `entity_ref` resolves to a `removed` Component
- **THEN** that step's node shows a visible removed-status warning indicator

#### Scenario: A step referencing a deprecated entity shows a distinct warning indicator
- **WHEN** a Flow's diagram renders a step whose `entity_ref` resolves to a `deprecated` (but active) Resource
- **THEN** that step's node shows a visible deprecated-status warning indicator, visually distinguished from the removed-status indicator

#### Scenario: A step referencing an active, non-deprecated entity shows no warning
- **WHEN** a Flow's diagram renders a step whose reference resolves to an entity that is `active` and not `deprecated`
- **THEN** no warning indicator is shown on that node
