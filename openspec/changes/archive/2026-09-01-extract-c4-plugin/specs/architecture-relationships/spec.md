## MODIFIED Requirements

### Requirement: Explicit User and Group interactions are represented as C4 People
The system SHALL allow any catalog entity whose kind declares the `architecture.actor.v1` capability (which `group` and `actor` — renamed from `user` in `introduce-catalog-entity-identity` — both declare) as an Architecture Relationship endpoint. A System Context diagram SHALL render an explicitly related capability-declaring entity as a C4 Person, while ownership alone SHALL not render a Person.

#### Scenario: Explicit actor interaction appears as a person
- **WHEN** a catalog entity whose kind declares `architecture.actor.v1` (e.g. an Actor or a Group) has an explicit Architecture Relationship to a System or Component in the selected System's context
- **THEN** the System Context diagram includes that entity as a Person and renders the declared interaction

#### Scenario: A future capability-declaring kind needs no C4 change
- **WHEN** a new Entity Kind is registered declaring `architecture.actor.v1`
- **THEN** its entities render as C4 People when explicitly related, without any change to the C4 plugin's own code
