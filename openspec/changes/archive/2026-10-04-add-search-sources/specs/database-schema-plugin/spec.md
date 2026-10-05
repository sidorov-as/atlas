## ADDED Requirements

### Requirement: Schema facets record creation and modification times
A database schema facet SHALL record when it was created and when it was last modified, set automatically on save, and the Django admin SHALL display both. Existing facets SHALL receive a creation time at migration.

#### Scenario: New schema facet
- **WHEN** a schema facet is created
- **THEN** its creation and modification times are set

#### Scenario: Schema edited
- **WHEN** a schema facet is saved after an edit
- **THEN** its modification time is updated and its creation time is unchanged

#### Scenario: Existing facets after migration
- **WHEN** the migration is applied to a database with existing facets
- **THEN** each facet has non-empty creation and modification times

#### Scenario: Admin shows the times
- **WHEN** an administrator opens a facet in the admin
- **THEN** the creation and modification times are visible and read-only
