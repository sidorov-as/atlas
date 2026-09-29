## ADDED Requirements

### Requirement: System Context Diagram is generated from System architecture data
The system SHALL generate a PlantUML-backed System Context Diagram for a System using explicit Architecture Relationships and cross-system catalog interactions. Ownership relations alone SHALL NOT create people or runtime edges. Systems tagged `External` SHALL render as external systems.

#### Scenario: Cross-system API use becomes a System Context edge
- **WHEN** a Component in System A consumes an API belonging to System B
- **THEN** System A's context diagram includes an interaction from System A to System B unless an explicit relationship for the same visible endpoints supersedes it

#### Scenario: Explicit actor interaction appears without ownership inference
- **WHEN** a User or Group has an explicit Architecture Relationship to a System or Component in the selected System
- **THEN** the context diagram renders that endpoint as a person and includes the declared edge

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
