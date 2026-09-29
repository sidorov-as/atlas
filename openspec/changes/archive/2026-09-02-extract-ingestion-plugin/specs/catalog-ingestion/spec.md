## MODIFIED Requirements

### Requirement: Basic ingestion upsert
Given a registered repository containing a valid `catalog-info.yaml`, ingestion SHALL create or update every entity in the file to match, and re-ingesting the same file SHALL update the same entity rather than creating a duplicate. Every such create or update SHALL be performed through the core Entity Service via an `EntityIntent`, not by writing catalog models directly.

#### Scenario: First ingestion creates entities
- **WHEN** the ingestor runs against a repository with a valid manifest for the first time
- **THEN** every entity in the file exists in the catalog with fields matching the file, marked YAML-managed

#### Scenario: Re-ingestion updates in place
- **WHEN** a `catalog-info.yaml` is edited and pushed, and the ingestor next runs
- **THEN** the corresponding entity's fields are updated to match, without creating a duplicate entity

#### Scenario: Upsert is indistinguishable from a manual write at the Entity Service boundary
- **WHEN** ingestion creates or updates an entity
- **THEN** the same common-metadata validation and audit recording that a manual API write would trigger also runs for the ingestion write
