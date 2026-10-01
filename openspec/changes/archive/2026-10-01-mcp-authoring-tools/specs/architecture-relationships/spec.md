## ADDED Requirements

### Requirement: Manual relationship management is a published service contract
The system SHALL publish manual Architecture Relationship list, create, update, and delete as a service contract usable by plugins, and the REST controllers SHALL perform those operations through it. The service SHALL take the acting user, SHALL create relationships only with origin `manual`, SHALL reject mutation of YAML-origin relationships, SHALL require write permission on the source entity, and SHALL ensure referenced tags exist. Behavior observable through the existing REST endpoints SHALL be unchanged.

#### Scenario: REST and another caller share the same rules
- **WHEN** a manual relationship is created through the REST endpoint and through the published service by the same user
- **THEN** both produce the same record shape, and both are rejected under the same permission and origin conditions

#### Scenario: YAML-origin relationship is protected at the service level
- **WHEN** any caller attempts through the service to update or delete a YAML-origin relationship
- **THEN** the service rejects the request and preserves the relationship

#### Scenario: Existing REST behavior is unchanged
- **WHEN** the existing architecture-relationship REST tests run after the service extraction
- **THEN** they pass without modification
