## ADDED Requirements

### Requirement: Ingestion is an optional platform plugin
Ingestion SHALL be provided entirely by the `atlas.ingestion` plugin; manual and REST-API entity management SHALL continue working unchanged when it is not selected.

#### Scenario: Distribution without atlas.ingestion composes successfully
- **WHEN** a distribution selects `atlas.standard-catalog` but not `atlas.ingestion`
- **THEN** composition succeeds, no ingestion scheduling runs, and manual entity CRUD via the API is unaffected

### Requirement: Connectors and parsers are plugin-owned extension points
`atlas.ingestion` SHALL publish `SourceConnector` and `DocumentParser` as its own versioned, keyed extension points; connector and parser implementations SHALL register against them rather than being hard-coded into the pipeline.

#### Scenario: GitHubConnector is a registered implementation, not a hard-coded call
- **WHEN** the ingestion pipeline discovers manifests
- **THEN** it does so by invoking the connector registered for the configured source, not by calling `GitHubConnector` directly by name

### Requirement: All entity changes flow through the core Entity Service
A connector's fetched Artifact SHALL be parsed into an `EntityIntent`, validated by the target kind's handler, and applied exclusively through the core Entity Service; no ingestion code path SHALL write a `CatalogEntity` or kind-details row directly.

#### Scenario: Ingestion upsert uses the Entity Service
- **WHEN** ingestion upserts an entity from a manifest
- **THEN** the write is performed by the same Entity Service used for manual and REST-API writes, with `source_kind=yaml` and the claiming repository recorded as part of that same call
