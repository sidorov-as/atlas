# ingestion-plugin Specification

## Purpose
Governs ingestion as an optional platform plugin — how it is packaged, how connectors and parsers are exposed as plugin-owned extension points, and how every entity change it makes flows through the core Entity Service rather than writing catalog models directly.

## Requirements

### Requirement: Ingestion is an optional platform plugin
Ingestion SHALL be provided entirely by the `atlas.ingestion` plugin; manual and REST-API entity management SHALL continue working unchanged when it is not selected.

#### Scenario: Distribution without atlas.ingestion composes successfully
- **WHEN** a distribution selects `atlas.standard-catalog` but not `atlas.ingestion`
- **THEN** composition succeeds, no ingestion scheduling runs, and manual entity CRUD via the API is unaffected

### Requirement: Connectors and parsers are plugin-owned extension points
`atlas.ingestion` SHALL publish `SourceConnector` and `DocumentParser` as its own versioned, keyed extension points; connector and parser implementations SHALL register against them rather than being hard-coded into the pipeline.

#### Scenario: GitConnector is a registered implementation, not a hard-coded call
- **WHEN** the ingestion pipeline discovers manifests for a registered repository
- **THEN** it does so by invoking the `GitConnector` registered against `atlas.ingestion.connectors.v1`, resolved via that repository's configured source, not by calling a provider-specific connector directly by name

### Requirement: The connector fetch path never invokes an external process
`GitConnector` SHALL implement both HTTPS and SSH git transport without invoking a subprocess (no shelling out to a `git` or `ssh` binary), to avoid transport-helper and SSH-argument injection classes of vulnerability.

#### Scenario: SSH fetch does not shell out
- **WHEN** `GitConnector` clones a source over `ssh://`
- **THEN** no subprocess is spawned to perform the clone; the SSH session is handled entirely within the Python process

### Requirement: All entity changes flow through the core Entity Service
A connector's fetched Artifact SHALL be parsed into an `EntityIntent`, validated by the target kind's handler, and applied exclusively through the core Entity Service; no ingestion code path SHALL write a `CatalogEntity` or kind-details row directly.

#### Scenario: Ingestion upsert uses the Entity Service
- **WHEN** ingestion upserts an entity from a manifest
- **THEN** the write is performed by the same Entity Service used for manual and REST-API writes, with `source_kind=yaml` and the claiming repository recorded as part of that same call
