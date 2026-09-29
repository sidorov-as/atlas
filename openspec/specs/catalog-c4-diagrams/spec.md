# catalog-c4-diagrams Specification

## Purpose

Generate local PlantUML-backed C4 diagrams from Atlas catalog data and serve them as images.

## Requirements

### Requirement: System Context Diagram is generated from System architecture data
The system SHALL generate a PlantUML-backed System Context Diagram for a System using explicit Architecture Relationships and cross-system catalog interactions. Ownership relations alone SHALL NOT create people or runtime edges. Systems tagged `External` SHALL render as external systems.

#### Scenario: Cross-system API use becomes a System Context edge
- **WHEN** a Component in System A consumes an API belonging to System B
- **THEN** System A's context diagram includes an interaction from System A to System B unless an explicit relationship for the same visible endpoints supersedes it

#### Scenario: Explicit actor interaction appears without ownership inference
- **WHEN** a User or Group has an explicit Architecture Relationship to a System or Component in the selected System
- **THEN** the context diagram renders that endpoint as a person and includes the declared edge

### Requirement: Catalog-wide System Landscape is generated from architecture data
The system SHALL generate a PlantUML-backed System Context Diagram for the entire catalog. It SHALL include every catalog System, include Users and Groups only when they are explicit Architecture Relationship endpoints, map System-bound relationship endpoints to their owning System, and combine declared Architecture Relationships with cross-system derived catalog interactions. A declared interaction SHALL supersede a derived fallback with the same directed visible endpoints.

#### Scenario: Landscape includes all systems and explicit people
- **WHEN** the catalog contains Systems and a User with an explicit Architecture Relationship to a Component
- **THEN** the System Landscape contains every System, the User as a C4 Person, and the User's relationship to the Component's System

#### Scenario: Landscape does not infer actors from ownership
- **WHEN** a User owns or belongs to a Group that owns catalog entities but has no explicit Architecture Relationship
- **THEN** the User and Group do not appear in the System Landscape

### Requirement: Catalog-wide System Landscape is served as an image
The diagram endpoint SHALL serve the catalog-wide System Landscape as SVG by default and support PNG and download behavior equivalent to existing diagram endpoints.

#### Scenario: User requests the default landscape image
- **WHEN** an authenticated user requests the System Landscape without a format parameter
- **THEN** the endpoint returns generated `image/svg+xml` content without requiring an entity id

#### Scenario: User downloads a PNG landscape image
- **WHEN** an authenticated user requests the System Landscape with `format=png` and download enabled
- **THEN** the endpoint returns an `image/png` attachment

### Requirement: Component Diagram has the requested System-and-selected-dependencies scope
The system SHALL generate a Component Diagram for a Component containing every Component in its System and every API and Resource directly related to the selected Component. The selected Component SHALL be visually distinguished, and endpoints outside the System SHALL render as external.

#### Scenario: Selected Component includes its resources and APIs
- **WHEN** a Component depends on a database and consumes an API
- **THEN** its Component Diagram includes every Component in its System, that database, and that API

#### Scenario: Resource rendering follows its catalog type
- **WHEN** a selected Component relates to a `database` Resource and a `queue` Resource
- **THEN** the diagram renders them as `ComponentDb` and `ComponentQueue` respectively

### Requirement: Generated diagrams are served as images
The diagram endpoint SHALL serve SVG by default and SHALL support PNG through an explicit format parameter for the System/context and Component/component target/view combinations. A download request SHALL return the requested image with attachment disposition.

#### Scenario: System Context defaults to SVG
- **WHEN** an authenticated user requests the context diagram for an existing System without a format parameter
- **THEN** the endpoint returns generated `image/svg+xml` content

#### Scenario: User requests PNG download
- **WHEN** an authenticated user requests a valid component diagram with `format=png` and `download=1`
- **THEN** the endpoint returns `image/png` with a download attachment header

#### Scenario: Unsupported target and view are rejected
- **WHEN** a user requests a diagram kind/view pair other than System/context or Component/component
- **THEN** the endpoint returns a client error without attempting to render

### Requirement: PlantUML rendering stays local to Atlas runtime
The backend SHALL create its diagram model with `c4-diagrams` and render it through a local PlantUML runtime, without calling a remote PlantUML server during diagram requests.

#### Scenario: Rendering works without outbound network access
- **WHEN** the backend container has no outbound network connectivity and a valid diagram is requested
- **THEN** rendering succeeds using the installed PlantUML binary and bundled C4-PlantUML includes

### Requirement: System Architecture images have a validated endpoint
The diagram endpoint SHALL accept `GET /api/diagrams/system/{id}/?view=architecture` and return a generated image in the same SVG-default, PNG, and download formats supported by the existing diagram endpoints.

#### Scenario: System Architecture defaults to SVG
- **WHEN** an authenticated user requests an existing System with `view=architecture`
- **THEN** the endpoint returns generated `image/svg+xml` content

### Requirement: Atlas C4 diagrams use stable configurable semantic styling
The system SHALL render System Context, System Architecture, Component, and
System Landscape diagrams with one of `LAYOUT_TOP_DOWN`, `LAYOUT_LEFT_RIGHT`,
or `LAYOUT_LANDSCAPE`, selected through a validated request option and
defaulting to `LAYOUT_TOP_DOWN`. The system SHALL support validated request
options to show or hide the diagram title, Atlas legend, selected-component
`(selected)` label, person sprites, and stereotypes; absent options SHALL
preserve the currently visible title, legend, selected label, person sprite,
and stereotypes. Hiding a selected-component label SHALL NOT remove its
semantic selected styling. Element styles SHALL include role-specific
background, font, border color, border style, border thickness, and deliberate
shadowing. Explicit Architecture Relationship interaction kinds SHALL map to
distinct solid, dashed, or dotted relationship tags; derived fallback edges
SHALL use a distinct derived tag. Free-form catalog metadata tags SHALL not
change generated diagram styling.

#### Scenario: Interaction kinds are visually distinguished
- **WHEN** a diagram contains synchronous, asynchronous, data-access, and manual Architecture Relationships
- **THEN** its rendered PlantUML model assigns a stable distinct color, line treatment, and legend entry to each interaction kind

#### Scenario: Diagram elements use rounded semantic roles
- **WHEN** a diagram contains an internal component, database, queue, and external endpoint
- **THEN** each renders as a rounded semantic role with the approved fixed palette and legend treatment

#### Scenario: Catalog metadata cannot arbitrarily restyle a diagram
- **WHEN** an entity has free-form catalog tags that are not Atlas diagram role tags
- **THEN** those tags do not change the generated PlantUML styling

#### Scenario: Valid display settings modify only their intended output
- **WHEN** a diagram request selects Left-right layout while hiding the title,
  legend, person sprites, and stereotypes
- **THEN** the PlantUML payload uses the Left-right layout and omits each
  requested presentation feature while retaining the diagram's elements,
  relationships, and fixed semantic styles

#### Scenario: Hiding the selected label retains selection styling
- **WHEN** a Component Diagram request disables the selected-component label
- **THEN** the selected component label omits `(selected)` and the element
  retains the selected-component semantic tag

#### Scenario: Invalid rendering option is rejected
- **WHEN** a diagram request supplies an unsupported layout or a malformed
  display option
- **THEN** the endpoint returns a client error without attempting to render an
  image
