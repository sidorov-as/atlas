# ui-theme Specification

## Purpose
TBD - light, dark, and system theme support for the Atlas UI. Created by syncing change dark-theme.

## Requirements

### Requirement: Theme mode is selectable as light, dark, or system
The application SHALL support three theme modes: `light`, `dark`, and `system`. In `system` mode the application SHALL follow the operating system's color-scheme preference and SHALL update when that preference changes. The default mode, when no choice has been stored, SHALL be `system`.

#### Scenario: Default follows the operating system
- **WHEN** a user opens Atlas with no stored theme choice and the operating system prefers dark
- **THEN** the application renders in its dark theme

#### Scenario: Explicit choice overrides the operating system
- **WHEN** a user selects `light` while the operating system prefers dark
- **THEN** the application renders in its light theme

#### Scenario: System mode tracks operating system changes
- **WHEN** the mode is `system` and the operating system preference changes from light to dark
- **THEN** the application switches to its dark theme without a reload

### Requirement: Theme switcher lives in the navigation shell footer
The authenticated navigation shell SHALL provide a theme switcher in its footer, alongside the signed-in user and the log-out action. When the shell is expanded the switcher SHALL show all three modes and indicate the active one. When the shell is collapsed it SHALL remain operable as a single icon control that cycles through the modes.

#### Scenario: Expanded shell shows all modes
- **WHEN** a user views an authenticated page with the sidebar expanded
- **THEN** the footer shows light, dark, and system options and marks the active one

#### Scenario: Collapsed shell keeps the switcher
- **WHEN** a user collapses the sidebar
- **THEN** the footer still offers a theme control that changes the mode when activated

#### Scenario: Choosing a mode applies it immediately
- **WHEN** a user selects `dark` in the switcher
- **THEN** the whole application, including already-open pages, renders in the dark theme without a reload

### Requirement: Theme choice is stored only in the browser
The selected theme mode SHALL be persisted in the browser's local storage and SHALL NOT be sent to or stored by the server. If local storage is unavailable or holds an unrecognized value, the application SHALL fall back to `system` and remain fully usable.

#### Scenario: Choice survives a reload
- **WHEN** a user selects `dark` and reloads the page
- **THEN** the application renders in the dark theme

#### Scenario: Choice is not shared across browsers
- **WHEN** a user selects `dark` in one browser and opens Atlas in another browser
- **THEN** the second browser uses its own stored choice, or `system` if it has none

#### Scenario: Unavailable or invalid storage falls back to system
- **WHEN** local storage throws on access or contains a value other than `light`, `dark`, or `system`
- **THEN** the application uses `system` and does not fail to render

### Requirement: The stored theme is applied before the application renders
The application SHALL apply the resolved theme to the document before the React application mounts, so that a reload does not show a flash of the wrong theme.

#### Scenario: Dark reload shows no light flash
- **WHEN** a user whose stored mode resolves to dark reloads any page
- **THEN** the document background is already dark from the first paint

### Requirement: Plugins can read the active theme
`core/frontend` SHALL export a theme context that exposes the selected mode and the resolved theme (`light` or `dark`), so plugin components can adapt to it without reading the document directly.

#### Scenario: Plugin component reads the resolved theme
- **WHEN** a plugin component reads the theme context while the mode is `system` and the operating system prefers dark
- **THEN** it receives the mode `system` and the resolved theme `dark`

### Requirement: Flow and ER canvases and exports follow the active theme
The Flows canvas and the database ER diagram SHALL render with the active theme's colors, including canvas background, grid, and controls. Their image exports SHALL be produced in the active theme: a non-transparent export SHALL use the active theme's page background color rather than a fixed white, and a transparent export SHALL remain transparent.

#### Scenario: Dark canvas
- **WHEN** a user views a flow or an ER diagram in the dark theme
- **THEN** the canvas, grid, nodes, and controls render with dark theme colors

#### Scenario: Non-transparent export uses the theme background
- **WHEN** a user exports a flow or ER diagram as PNG or SVG in the dark theme without transparency
- **THEN** the exported image has the dark theme's page background

#### Scenario: Transparent export is unchanged
- **WHEN** a user exports with transparency enabled
- **THEN** the exported image has no background fill in either theme

### Requirement: API documentation viewers follow the active theme
The OpenAPI and AsyncAPI documentation viewers SHALL render legibly in both themes, with background, text, code, and schema colors matching the active theme, and SHALL update when the theme changes.

#### Scenario: OpenAPI viewer in dark theme
- **WHEN** a user views an OpenAPI spec in the dark theme
- **THEN** the documentation renders with a dark background and light text, with no unreadable dark-on-dark regions

#### Scenario: AsyncAPI viewer in dark theme
- **WHEN** a user views an AsyncAPI spec in the dark theme
- **THEN** the documentation renders with a dark background and light text, with no unreadable dark-on-dark regions

#### Scenario: Viewer follows a theme change
- **WHEN** a user switches theme while an API documentation viewer is open
- **THEN** the viewer re-renders in the new theme
