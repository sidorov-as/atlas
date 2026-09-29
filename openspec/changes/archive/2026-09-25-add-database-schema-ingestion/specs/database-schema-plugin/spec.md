## ADDED Requirements

### Requirement: A YAML-managed Resource's Database Schema facet cannot be edited manually
Once a Resource entity is YAML-managed (`source_kind` is YAML), its `DatabaseSchema` Facet SHALL NOT be created or updated through the plugin's manual write endpoint, regardless of whether that Resource's current manifest declares `spec.databaseSchema`.

#### Scenario: Manual write is rejected on a YAML-managed Resource
- **WHEN** a user attempts to create or update the `DatabaseSchema` facet of a YAML-managed Resource through the plugin's write endpoint
- **THEN** the request is rejected and the facet's stored data is unchanged

#### Scenario: Manual write still succeeds on a non-YAML-managed Resource
- **WHEN** a user attempts to create or update the `DatabaseSchema` facet of a Resource that is not YAML-managed
- **THEN** the write succeeds as before

#### Scenario: A previously-attached facet is frozen once its Resource becomes YAML-managed
- **WHEN** a Resource with a manually-attached `DatabaseSchema` facet later becomes YAML-managed, whether or not its manifest declares `spec.databaseSchema`
- **THEN** the facet's existing data is not deleted by that transition alone, but further manual writes to it are rejected
