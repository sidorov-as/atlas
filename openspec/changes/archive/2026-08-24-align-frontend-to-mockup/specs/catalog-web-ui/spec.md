## ADDED Requirements

### Requirement: Entity list preview panel
System, Component, Resource, and API list pages SHALL open a right-side preview panel when a row is clicked, showing a summary of that entity with a link-through action to its full detail page, instead of navigating away immediately.

#### Scenario: Clicking a row opens the preview panel
- **WHEN** a user clicks a row in any of the four entity list pages
- **THEN** a right-side panel opens showing that entity's summary, and the underlying list remains visible

#### Scenario: Preview panel links through to the full detail page
- **WHEN** a user clicks the link-through button in the preview panel
- **THEN** they are navigated to that entity's full detail page

#### Scenario: Preview panel can be dismissed without navigating
- **WHEN** a user closes the preview panel (e.g. via a close control)
- **THEN** the panel closes, the user remains on the list page, and no navigation has occurred

### Requirement: Branded, collapsible navigation shell
The application SHALL show a sidebar with the Atlas logo and wordmark, an icon per navigation item, a collapse/expand control, and a Settings entry, on every authenticated page.

#### Scenario: Sidebar can be collapsed and expanded
- **WHEN** a user toggles the sidebar's collapse control
- **THEN** the sidebar collapses to icons-only, or expands back to icons and labels, consistently across all authenticated pages

#### Scenario: Settings entry is present
- **WHEN** a user views the sidebar
- **THEN** a "Settings" navigation entry is present alongside Systems/Components/Resources/APIs/Teams
