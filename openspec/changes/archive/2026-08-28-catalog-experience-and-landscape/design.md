## Context

Atlas already has separate derived `Relation` records, directed authored `ArchitectureRelationship` records, local PlantUML-backed C4 payload generation, a reusable diagram viewer, and a card-only homepage. The list preview component is shared, but Teams wraps only its table and rail in a flex row whereas the reusable entity list wraps its heading as well. Architecture relationship listing currently filters only by source, while diagram builders already consider both endpoints for visibility.

The requested homepage follows the EventCatalog information hierarchy: catalog title, description, divider, navigation cards, then a catalog-wide context map. The title and description are deployment configuration, not catalog content managed by individual users.

## Goals / Non-Goals

**Goals:**

- Make all list preview rails begin beside their respective table content.
- Let Relations tabs disclose an Architecture Relationship from either endpoint without obscuring its directed source-to-target meaning or changing source-based write authorization.
- Establish an Atlas-owned rounded semantic C4 visual system using the approved reference palette.
- Render a locally generated catalog-wide system landscape on the homepage with the existing pan/zoom/download viewer.
- Supply the homepage title and description from Django configuration.

**Non-Goals:**

- Do not make Architecture Relationships bidirectional records or synthesize reverse edges.
- Do not change the accepted rule that a declared edge supersedes a derived edge with the same directed endpoints; multiple declared edges with identical direction retain existing last-record rendering behavior.
- Do not infer people from ownership, introduce domains, or replace the existing system-specific context/architecture/component diagrams.
- Do not create an in-app editor for the Django-configured title or description.

## Decisions

### 1. Separate page chrome from the list-and-preview content row

The shared entity-list page will render heading, description, filters, and messages above a flex row containing table/pagination and the optional preview rail, matching the Teams page. This keeps preview alignment stable and avoids a Team-only visual exception.

Alternative: move the Teams heading into its flex row. Rejected because it preserves the less useful header-aligned rail behavior on every list page.

### 2. Return relationship participation, not a fabricated reverse relationship

The Architecture Relationship list query will select rows where the requested entity is source **or** target. Responses will continue to return canonical `source`, `target`, direction, origin, and metadata. The Relations UI will label/render both endpoints, make outgoing versus incoming status clear, and expose edit/delete only for manual rows whose source is the current manual entity. Catalog Relations remain their separately derived, subject-oriented list.

Alternative: create a reverse ArchitectureRelationship row. Rejected because it duplicates authored runtime intent, complicates edit/delete and YAML reconciliation, and would cause a second diagram edge.

### 3. Provide homepage identity through Django settings and an authenticated read endpoint

Introduce `CATALOG_TITLE` and `CATALOG_DESCRIPTION` Django settings with Atlas defaults. A small catalog configuration endpoint exposes their effective values to the React home page; it does not allow mutation. This is explicit, deployment-friendly, and avoids coupling the frontend build to backend environment configuration.

Alternative: hard-code strings in React. Rejected because deployments cannot brand the catalog without rebuilding the frontend. Alternative: persist mutable site settings in a model. Rejected because the request calls for Django settings and no administrative editing workflow is in scope.

### 4. Treat the landscape as a first-class, unscoped C4 System Context diagram

Add a C4 payload builder and diagram endpoint with no entity id. It includes every System, plus Users/Groups only when explicitly present in an Architecture Relationship. It combines every declared relationship after mapping system-bound endpoints to their systems with cross-system derived relations. Edge merging uses the existing directed endpoint key and declared-over-derived precedence. The homepage uses the existing `DiagramViewer`, including SVG/PNG download controls.

Alternative: stitch together existing per-System Context diagrams client-side. Rejected because it would duplicate nodes and edges, lose server-side deduplication, and cannot produce one coherent PlantUML layout.

### 5. Centralize the approved visual language in C4 payload styles

Replace the current minimal tag definitions with fixed role/interactions styles derived from `local/diagram_colors.json`: rounded boxes, role-specific background/font/border colors, border styles/thicknesses, deliberate shadowing, and solid/dashed/dotted relationships. The mapping remains based only on Atlas role and interaction tags; arbitrary entity tags remain unable to alter C4 style.

Alternative: pass catalog tags through to PlantUML styling. Rejected because it makes diagrams unpredictable and violates the established stable-semantic-style contract.

## Risks / Trade-offs

- [A full landscape can become visually dense as the catalog grows] → retain pan/zoom/fit/download, top-down deterministic layout, and include only explicit actors; consider filtering/grouping only in a future change.
- [Incoming rows could look editable from a target page] → return and display canonical source, then gate controls on current entity being the manual relationship's source.
- [Django settings need to be available in all deploy modes] → provide documented defaults and test override behavior.
- [Style changes alter existing snapshot-like generated SVG output] → add payload-level style assertions and renderer/UI coverage for all diagram scopes.

## Migration Plan

1. Deploy additive settings defaults, API endpoint, and landscape endpoint.
2. Deploy frontend usage; existing entity detail and diagram URLs remain valid.
3. Roll back frontend independently if needed; new endpoints/settings are additive and do not migrate catalog data.
