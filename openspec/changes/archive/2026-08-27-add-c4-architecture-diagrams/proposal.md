## Why

The System and Component C4 Diagram tabs currently return a static SVG placeholder, so Atlas cannot demonstrate its central promise: catalog metadata and declared architecture interactions as an executable source of truth for architecture diagrams. Existing derived catalog relations capture ownership and structural references, but cannot preserve the business label, technology, direction, and interaction kind required for meaningful C4 relationships.

## What Changes

- Add a first-class, directed Architecture Relationship model for declared runtime and architecture interactions, separate from Atlas's derived read-only catalog `Relation` records.
- Allow Architecture Relationships to be managed through manual CRUD and declared in YAML manifests; expose them separately from derived relations in the Relations tab.
- Generate PlantUML-backed C4 diagrams from catalog metadata and Architecture Relationships with `c4-diagrams`, returning SVG for display and SVG/PNG for download.
- Replace the System Context and Component Diagram placeholders with responsive, full-width interactive viewers featuring pan, zoom in/out, fit-to-viewport, and image download.
- Add the `c4-diagrams` backend dependency and a local PlantUML runtime to the backend Docker image.

## Capabilities

### New Capabilities

- `architecture-relationships`: Declared, directed architecture interactions with human-readable C4 relationship metadata, manual/YAML provenance, and relation-management UI.
- `catalog-c4-diagrams`: Metadata-driven System Context and Component Diagram generation, rendering, download, and interactive display.

### Modified Capabilities

- `catalog-ingestion`: Ingest declared Architecture Relationships from the Atlas catalog manifest format after entity resolution.
- `containerized-runtime`: Provide a local PlantUML runtime in the backend image for offline C4 SVG/PNG rendering.
- `catalog-web-ui`: Give System and Component C4 tabs a full-width interactive diagram viewer and add editable architecture relationships to entity relation views.
- `diagram-stub`: Replace the placeholder diagram response with validated generated System Context and Component Diagram images.

## Impact

- Backend catalog models, migrations, reference resolution, permissions, schemas, relation endpoints, YAML ingestion pipeline, diagram endpoint, tests, and demo data change.
- Frontend entity types, relation tabs/forms, System and Component detail-page layout, diagram viewer, styling, and tests change.
- Backend adds `c4-diagrams`; backend Docker stages install Java and PlantUML. No remote rendering service is required.
