## ADDED Requirements

### Requirement: Flows record creation and modification times
A flow SHALL record when it was created and when it was last modified, set automatically on save, and the Django admin SHALL display both. Existing flows SHALL receive a creation time at migration.

#### Scenario: New flow
- **WHEN** a flow is created
- **THEN** its creation and modification times are set

#### Scenario: Flow edited
- **WHEN** a flow is saved after an edit
- **THEN** its modification time is updated and its creation time is unchanged

#### Scenario: Existing flows after migration
- **WHEN** the migration is applied to a database with existing flows
- **THEN** each flow has non-empty creation and modification times

#### Scenario: Admin shows the times
- **WHEN** an administrator opens a flow in the admin
- **THEN** the creation and modification times are visible and read-only
