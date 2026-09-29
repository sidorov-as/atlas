## MODIFIED Requirements

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
- **WHEN** a diagram contains synchronous, asynchronous, data-access, and
  manual Architecture Relationships
- **THEN** its rendered PlantUML model assigns a stable distinct color, line
  treatment, and legend entry to each interaction kind

#### Scenario: Diagram elements use rounded semantic roles
- **WHEN** a diagram contains an internal component, database, queue, and
  external endpoint
- **THEN** each renders as a rounded semantic role with the approved fixed
  palette and legend treatment

#### Scenario: Catalog metadata cannot arbitrarily restyle a diagram
- **WHEN** an entity has free-form catalog tags that are not Atlas diagram role
  tags
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
