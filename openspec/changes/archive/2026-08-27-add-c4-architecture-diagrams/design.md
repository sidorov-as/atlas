## Context

Atlas currently derives read-only `Relation` rows from entity specification references and exposes them in a single Relations table. Its C4 endpoint accepts a broad target/view combination but returns one constant SVG. The frontend renders that SVG as a regular image in the constrained main column of the shared entity-detail layout.

The desired diagrams need two complementary sources of truth. Catalog structure already describes component membership, APIs, and resources. A C4 edge also needs architectural intent that structural references cannot express: a business label, technology/protocol, interaction kind, and directed relationship. The existing Backstage proof of concept encodes that extra intent in metadata annotations; Atlas can model it natively.

## Goals / Non-Goals

**Goals:**

- Preserve derived catalog relations as a reliable, immutable projection of entity specs.
- Add explicit architecture interactions that work for manual and YAML-managed catalog data.
- Generate a System Context for each System and a Component Diagram for each Component entirely from Atlas data using local PlantUML rendering.
- Make diagrams readable and useful in the browser through a full-width canvas-like viewer.

**Non-Goals:**

- Adding a generic graph editor, arbitrary PlantUML source editing, or user-configurable PlantUML macros/styles.
- Replacing the existing Component/Resource/API ownership model or treating owner/team relations as runtime interactions.
- Adding a new Actor entity in this change; existing User and Group entities are available as architecture-relation endpoints when appropriate.
- Caching diagrams, asynchronous render jobs, D2/Mermaid output, or arbitrary C4 diagram types.

## Decisions

### 1. Keep derived catalog relations and declared Architecture Relationships as separate models

`Relation` remains an internal, regenerated projection with its existing predicate mirrors. Add an `ArchitectureRelationship` model with directed source/target catalog references, display label, optional technology, interaction kind (`synchronous`, `asynchronous`, `data-access`, or `manual`), tags, and managed origin (`manual` or `yaml`).

This avoids the unsafe alternative of making rows in the signal-regenerated `Relation` table editable. The UI can present both in one Relations tab, but their lifecycle and meaning remain explicit. An Architecture Relationship is intentionally renderer-neutral; C4/PlantUML maps it to `REL` plus renderer tags rather than persisting PlantUML macro names.

### 2. Make declared relationships part of entity `spec`

YAML manifests declare outgoing `spec.relationships` using target refs and the Architecture Relationship attributes. The ingestion pipeline first resolves/upserts entities, then resolves and reconciles their outgoing declared relationships; this permits references to entities elsewhere in the same multi-document manifest. Manual relationships are maintained by protected API endpoints and are not overwritten by ingestion.

Metadata labels stay scalar key/value catalog metadata and are not used as a JSON escape hatch. YAML-managed entities expose declared relationships read-only in the web UI, consistent with their existing source-management policy.

### 3. Produce deterministic diagram scopes from the catalog

A System Context has the selected System at its center, includes systems reached by declared interactions across system boundaries, and aggregates cross-boundary component/API/resource interactions into System-to-System edges when no explicit System-level edge supersedes them. User and Group endpoints are rendered as people when they participate in an interaction; ownership alone never makes an actor appear. A System tagged `External` is rendered as an external system.

A Component Diagram includes every Component in the selected Component's System, highlights the selected Component, and includes every API and Resource directly related to that selected Component. Direct declared architecture relationships and derived API/resource references between visible elements become diagram edges. Resources map deterministically: database to `ComponentDb`, queue to `ComponentQueue`, and cache/bucket/cluster to `Component`; APIs become external components when their System is external, otherwise components. Elements outside the selected System are external.

The renderer emits a stable Atlas PlantUML style, including layout, legend, and properties derived from entity type, owner, lifecycle, labels, and tags. It does not infer arbitrary visual styles from arbitrary catalog tags.

### 4. Render with `c4-diagrams` and local PlantUML, and make SVG the display format

The backend constructs strict PlantUML JSON dictionaries, converts them through `c4-diagrams`, and renders with `LocalPlantUMLBackend`. The Docker image installs a Java-backed PlantUML binary and `c4-diagrams` bundles its C4-PlantUML includes, avoiding network access at request time.

`GET /api/diagrams/system/{id}/?view=context` and `GET /api/diagrams/component/{id}/?view=component` serve SVG by default; a `format=png` option supports raster export and `download=1` supplies an attachment response. Invalid kind/view combinations retain clear client errors. Renderer failures return a controlled server error without exposing generated source or host paths.

### 5. Use a reusable full-width diagram viewer rather than a static image

The detail-page chrome gains a tab capability to render selected content outside the normal main-column/right-rail split. System and Component C4 tabs use it for a responsive viewer with pointer pan, zoom controls matching Flow Graph, fit-to-viewport, accessible tooltips, load/error states, and a download action. The viewer consumes same-origin image URLs so session authentication remains cookie based.

## Risks / Trade-offs

- [Large diagrams can make a synchronous request slow] → enforce a PlantUML timeout, construct scoped diagrams only, and add request-level error handling; caching can be introduced later if measurements require it.
- [Explicit edges duplicate a derived spec relation] → prefer the explicit Architecture Relationship for the same directed visible endpoints and retain derived relations only as fallback edges.
- [YAML references can cross document order] → reconcile declared relationships after the manifest's entities are resolved, report unresolved references as manifest errors, and do not create partial relationship rows.
- [User/Group catalog records can represent ownership rather than an actor] → render them only when an explicit architecture interaction names them.
- [PlantUML image rendering needs OS packages] → install and smoke-test the same backend image targets used by backend, initializer, and ingestor.

## Migration Plan

1. Add the Architecture Relationship table and non-destructive migration; existing derived `Relation` rows and entity specs remain unchanged.
2. Release read/render support with empty relationship sets producing valid diagrams, then introduce manual authoring and YAML declaration/reconciliation.
3. Build and test both Docker targets so the local renderer exists before enabling the generated endpoint in deployed Compose services.
4. Roll back application code safely without dropping the additive relationship table; retained declared rows are inert until a compatible version is restored.

## Open Questions

- None blocking. SVG is the in-browser and default download format; PNG is available through the same endpoint for consumers that require a raster image.
