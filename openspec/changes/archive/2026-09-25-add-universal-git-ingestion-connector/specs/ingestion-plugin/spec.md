## MODIFIED Requirements

### Requirement: Connectors and parsers are plugin-owned extension points
`atlas.ingestion` SHALL publish `SourceConnector` and `DocumentParser` as its own versioned, keyed extension points; connector and parser implementations SHALL register against them rather than being hard-coded into the pipeline.

#### Scenario: GitConnector is a registered implementation, not a hard-coded call
- **WHEN** the ingestion pipeline discovers manifests for a registered repository
- **THEN** it does so by invoking the `GitConnector` registered against `atlas.ingestion.connectors.v1`, resolved via that repository's configured source, not by calling a provider-specific connector directly by name

## ADDED Requirements

### Requirement: The connector fetch path never invokes an external process
`GitConnector` SHALL implement both HTTPS and SSH git transport without invoking a subprocess (no shelling out to a `git` or `ssh` binary), to avoid transport-helper and SSH-argument injection classes of vulnerability.

#### Scenario: SSH fetch does not shell out
- **WHEN** `GitConnector` clones a source over `ssh://`
- **THEN** no subprocess is spawned to perform the clone; the SSH session is handled entirely within the Python process
