## ADDED Requirements

### Requirement: Diagram endpoints accept an optional theme
Every C4 diagram endpoint SHALL accept an optional validated `theme` option with the values `light` and `dark`. An absent option SHALL be treated as `light`, producing output identical to that before the option existed. An invalid value SHALL be rejected with a client error before any rendering. The option SHALL apply to SVG and PNG output and to download requests alike.

#### Scenario: Absent theme renders light
- **WHEN** a diagram is requested without a `theme` option
- **THEN** the response is the same light-palette diagram as before the option existed

#### Scenario: Dark theme is requested
- **WHEN** an authenticated user requests a diagram with `theme=dark`
- **THEN** the endpoint returns the diagram rendered with the dark palette

#### Scenario: Invalid theme is rejected
- **WHEN** a diagram is requested with `theme=sepia`
- **THEN** the endpoint returns a client error without attempting to render

#### Scenario: Dark PNG download
- **WHEN** a user requests `format=png`, `download=1`, and `theme=dark`
- **THEN** the endpoint returns a PNG attachment rendered with the dark palette

### Requirement: Dark rendering uses a dedicated semantic palette
A dark-theme diagram SHALL use a dedicated palette for the diagram background, title, text, element tags, relationship tags, boundaries, and legend. Every role and interaction distinction that the light palette makes (selected, component, database, queue, endpoint, external endpoint, person; synchronous, asynchronous, data-access, manual, derived) SHALL remain visually distinguishable in the dark palette, and all text SHALL remain legible against its background. The dark palette SHALL be stable and SHALL NOT be influenced by free-form catalog metadata tags.

#### Scenario: Roles stay distinguishable in dark
- **WHEN** a dark diagram contains a selected component, a database, a queue, and a person
- **THEN** each renders with its own stable background and border treatment and its own legend entry

#### Scenario: Interaction kinds stay distinguishable in dark
- **WHEN** a dark diagram contains synchronous, asynchronous, data-access, and manual relationships
- **THEN** each keeps its distinct color and line treatment, legible against the dark background

#### Scenario: Boundaries, title, and legend are legible
- **WHEN** a dark diagram shows a boundary, a title, and the legend
- **THEN** their text and borders contrast with the dark background and none render as dark-on-dark

#### Scenario: Dark output is deterministic
- **WHEN** the same diagram is requested twice with `theme=dark` and no catalog change
- **THEN** both responses contain the same diagram content
