## ADDED Requirements

### Requirement: Fetched content is bounded before parsing
Any content fetched by a connector on behalf of the ingestion pipeline — a discovered manifest, an `Include`-resolved fragment, or a `sourceSqlPath`-resolved file — SHALL be subject to a configured maximum byte size, and any YAML parsed from that content SHALL be subject to a configured maximum document size and nesting depth. Content exceeding either limit SHALL be rejected and reported as a failed resolution for that path, without blocking ingestion of the rest of the repository's manifests.

#### Scenario: An oversized fetched file is rejected before parsing
- **WHEN** a connector fetches a file whose size exceeds the configured maximum fetched-file size
- **THEN** the file is rejected and reported as a failed resolution, and it is not passed to the YAML parser

#### Scenario: Excessively nested YAML is rejected
- **WHEN** a fetched manifest or fragment parses as YAML whose nesting depth exceeds the configured maximum
- **THEN** the document is rejected and reported as a failed resolution, and ingestion of the rest of the repository's manifests proceeds unaffected
