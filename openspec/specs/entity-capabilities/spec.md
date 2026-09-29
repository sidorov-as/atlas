# entity-capabilities Specification

## Purpose

Defines semantic capabilities that Entity Kinds declare, so that contributions target capabilities instead of hard-coded kind lists while kind-specific predicates remain valid.

## Requirements

### Requirement: Entity Kinds declare semantic capabilities
An Entity Kind's registration SHALL be able to declare a list of semantic capability identifiers it provides, independent of any particular consuming plugin.

#### Scenario: A kind declares a capability
- **WHEN** the `system` kind is registered declaring `provides=["architecture.subject.v1"]`
- **THEN** the capability registry records that `system` provides `architecture.subject.v1`

### Requirement: Contributions target capabilities, not hard-coded kind lists
A cross-plugin contribution MAY target entities by declared capability (`entitySupports(capability)`); it SHALL NOT need to enumerate specific kind ids to do so.

#### Scenario: A capability-targeted tab applies to any capable kind
- **WHEN** a contribution targets `entitySupports('architecture.subject.v1')`
- **THEN** it applies to every currently registered kind declaring that capability, without the contribution's code naming those kinds

#### Scenario: A newly capable kind gains the contribution without it changing
- **WHEN** a new Entity Kind is registered also declaring `architecture.subject.v1`
- **THEN** the existing capability-targeted contribution applies to the new kind without any change to the contributing plugin's code

### Requirement: Kind-specific predicates remain valid
The contribution contract SHALL continue to support targeting a specific kind id directly, for contributions whose behavior is genuinely specific to one kind.

#### Scenario: A kind-specific tab is unaffected by capability targeting
- **WHEN** a contribution targets a specific `kind` id rather than a capability
- **THEN** it applies only to that kind, unaffected by any other kind's declared capabilities
