# expand-contract-migrations Specification

## Purpose
A plugin's (and Core's) migrations follow enforced expand/contract discipline across a rolling deployment; a destructive migration is blocked by a linter unless the deployment explicitly opts into maintenance mode.

## Requirements

### Requirement: Destructive migrations are blocked outside maintenance mode
A migration that drops a column or table, or narrows a field's nullability without a default, SHALL be blocked by CI unless the deployment explicitly opts into a maintenance-mode override.

#### Scenario: A destructive migration is blocked
- **WHEN** a migration drops a column with no maintenance-mode override
- **THEN** CI fails, identifying the destructive operation

#### Scenario: An explicitly marked maintenance-mode migration is allowed
- **WHEN** a migration is marked as an explicit maintenance-mode change with a justification
- **THEN** CI allows it despite containing a destructive operation

### Requirement: New required fields are added compatibly
A newly required field SHALL be introduced as nullable or defaulted before any later migration makes it strictly required.

#### Scenario: A required field is added in two steps
- **WHEN** a plugin needs to add a new required field to an existing model
- **THEN** it first adds the field as nullable or defaulted, and only a later, separate migration removes that nullability

### Requirement: A plugin's migrations depend only on core and its own history
A plugin's migrations SHALL declare dependencies only on Core's migrations and its own prior migrations, never on another plugin's migrations or models.

#### Scenario: Cross-plugin migration dependency is rejected
- **WHEN** a plugin's migration declares a dependency on another plugin's migration
- **THEN** the import-boundary/migration check rejects it
