## MODIFIED Requirements

### Requirement: Flow diagram nodes visibly flag a removed or deprecated referenced entity

A step's node whose resolved reference (`entity_ref`, `query_ref`, or `event_ref`) currently carries `status: removed` or `deprecated: true` SHALL render a visible warning indicator on the node, distinguishing removed from deprecated, on both the read-only detail page and the edit page's canvas. An Event node whose stored `event_ref.direction`/`event_ref.channel` disagrees with its resolved Operation's current `direction`/`channel_address` SHALL additionally render this warning indicator, distinguished from the removed/deprecated indicators, even when the Operation itself is `active` and not deprecated.

#### Scenario: A step referencing a removed entity shows a warning indicator

- **WHEN** a Flow's diagram renders a step whose `entity_ref` resolves to a `removed` Component
- **THEN** that step's node shows a visible removed-status warning indicator

#### Scenario: A step referencing a deprecated entity shows a distinct warning indicator

- **WHEN** a Flow's diagram renders a step whose `entity_ref` resolves to a `deprecated` (but active) Resource
- **THEN** that step's node shows a visible deprecated-status warning indicator, visually distinguished from the removed-status indicator

#### Scenario: A step referencing an active, non-deprecated entity shows no warning

- **WHEN** a Flow's diagram renders a step whose reference resolves to an entity that is `active` and not `deprecated`
- **THEN** no warning indicator is shown on that node

#### Scenario: An Event node whose direction/channel has drifted shows a warning indicator

- **WHEN** a Flow's diagram renders an Event step whose stored `event_ref.direction`/`event_ref.channel` disagrees with its resolved Operation's current `direction`/`channel_address`, and that Operation is `active` and not deprecated
- **THEN** the node shows a visible warning indicator for the drift, even though neither removed nor deprecated is true
