## ADDED Requirements

### Requirement: Registered repository configuration
A Registered Repository SHALL hold `{owner/repo, default branch, access token}` as operational config, managed via Django admin.

#### Scenario: Repository registered via admin
- **WHEN** an operator adds a Registered Repository through Django admin with an owner/repo and access token
- **THEN** the ingestor includes it in the next discovery run

### Requirement: Manifest discovery via the connector interface
On each run, the connector SHALL list files matching `**/catalog-info.yaml` in each registered repository's default branch, and `GitHubConnector` SHALL be the only v1 implementation of that interface.

#### Scenario: Discovery finds a nested manifest
- **WHEN** a registered repository contains `services/user-management/catalog-info.yaml`
- **THEN** the connector's `list_manifest_paths` includes that path

### Requirement: Basic ingestion upsert
Given a registered repository containing a valid `catalog-info.yaml`, ingestion SHALL create or update every entity in the file to match, and re-ingesting the same file SHALL update the same entity rather than creating a duplicate.

#### Scenario: First ingestion creates entities
- **WHEN** the ingestor runs against a repository with a valid manifest for the first time
- **THEN** every entity in the file exists in the catalog with fields matching the file, marked YAML-managed

#### Scenario: Re-ingestion updates in place
- **WHEN** a `catalog-info.yaml` is edited and pushed, and the ingestor next runs
- **THEN** the corresponding entity's fields are updated to match, without creating a duplicate entity

### Requirement: Per-manifest failure isolation
A manifest document that fails schema validation SHALL be skipped and logged for that run, without rolling back other entities ingested from the same run.

#### Scenario: One invalid document doesn't block the rest
- **WHEN** a manifest with an invalid `kind` or a missing required `spec` field is processed in the same run as other valid documents
- **THEN** the invalid document is skipped and logged, and the other valid documents in the same run still ingest successfully

### Requirement: Multi-document manifests
A single `catalog-info.yaml` SHALL support multiple `---`-separated documents, each ingested as a separate entity.

#### Scenario: One file declares a System and its Components
- **WHEN** a manifest contains three `---`-separated documents (one System, two Components)
- **THEN** all three entities are created or updated from that single file
