## 1. Architecture Relationship domain and persistence

- [x] 1.1 Add the `ArchitectureRelationship` model, enums, constraints, admin registration, and additive Django migration while preserving the existing derived `Relation` model unchanged.
- [x] 1.2 Add shared ref resolution, ownership permission checks, serializers, and protected CRUD/list endpoints for directed manual Architecture Relationships.
- [x] 1.3 Extend catalog entity API responses/types to expose architecture relationships separately from derived catalog relations, including origin, label, technology, interaction kind, tags, and navigable target identity.
- [x] 1.4 Add backend tests for manual relationship validation, authorization, directed lifecycle, YAML read-only enforcement, and isolation from derived relation recomputation.

## 2. Manifest declarations and ingestion reconciliation

- [x] 2.1 Extend entity spec schemas and YAML validation with `relationships` declarations and strict fields for target, label, technology, interaction kind, and tags.
- [x] 2.2 Implement a post-upsert manifest reconciliation pass that resolves outgoing YAML declarations independently of document ordering, upserts YAML-origin relationships, and removes obsolete YAML-origin relationships without touching manual rows.
- [x] 2.3 Add ingestion tests for valid declarations, cross-document ordering, re-ingestion removal, malformed fields, unresolved targets, and per-manifest failure isolation.
- [x] 2.4 Add representative architecture interactions to the booking demo seed/catalog fixtures, including synchronous API use, asynchronous queue use, data access, and an external dependency.

## 3. Local C4 rendering foundation

- [x] 3.1 Add the published `c4-diagrams` dependency to backend package metadata and lockfile, and create an isolated catalog C4 rendering module.
- [x] 3.2 Install Java and PlantUML in the backend base Docker stage so development and production targets can invoke the local renderer without source-mounted dependency loss.
- [x] 3.3 Implement strict PlantUML JSON builders, stable Atlas render options/properties, aliases, external-system detection, and safe renderer error translation.
- [x] 3.4 Add Docker/backend smoke coverage that proves a local SVG render succeeds with no remote PlantUML service.

## 4. Diagram construction and image API

- [x] 4.1 Build System Context scopes from explicit system interactions and aggregated cross-system component/API/resource interactions, including explicit User/Group actors but excluding ownership-only actors.
- [x] 4.2 Build Component Diagram scopes with every Component in the selected System, highlighted selected Component, directly related APIs/Resources, deterministic resource/API element mapping, and external endpoint treatment.
- [x] 4.3 Merge explicit and derived fallback diagram edges deterministically so declared Architecture Relationships replace duplicate generic edges.
- [x] 4.4 Replace the placeholder diagram controller with System/context and Component/component validation, SVG-default/PNG format support, download disposition, and controlled rendering failures.
- [x] 4.5 Add backend tests for diagram scope composition, type mapping, explicit-edge precedence, SVG/PNG/download responses, invalid target/view pairs, and renderer failure handling.

## 5. Relations authoring and diagram viewer UI

- [x] 5.1 Split the Relations tab into labeled Catalog Relations and Architecture Relationships sections with target navigation and architecture relationship metadata.
- [x] 5.2 Add create, edit, and delete controls for outgoing manual Architecture Relationships, and explicit read-only states for YAML-origin relationships.
- [x] 5.3 Extend shared entity-detail chrome to support full-width tab content while preserving the existing right rail for ordinary tabs.
- [x] 5.4 Replace the static diagram image with a reusable viewer supporting image load/error states, pointer pan, Zoom in, Zoom out, Fit to viewport, and accessible tooltips.
- [x] 5.5 Connect System/context and Component/component tabs to the generated SVG endpoint and implement SVG/PNG download requests.
- [x] 5.6 Add frontend tests for relation section separation and permissions, YAML read-only display, full-width C4 tabs, viewer controls, download URLs, and image error states.

## 6. End-to-end verification

- [x] 6.1 Run Django migration checks and targeted catalog, ingestion, and diagram test suites; resolve regressions in existing derived relations and entity CRUD.
- [x] 6.2 Run frontend unit tests, typecheck, lint, and production build; verify the viewer in the System and Component detail layouts.
- [x] 6.3 Build both backend Docker targets and run the Compose topology smoke path that renders a generated diagram using local PlantUML.
- [x] 6.4 Validate the OpenSpec change and update any design/spec/task details discovered during verification before implementation completion.
