## ADDED Requirements

### Requirement: Flow list preview panel and row actions
The Flows list page SHALL open a right-side preview panel when a row is clicked, showing a summary of that Flow with a link-through action to its full detail page, matching the preview-panel behavior of the Systems/Components/Resources/APIs/Teams list pages. A second, fast click on a row already open in the preview panel SHALL navigate to that Flow's detail page. Every row SHALL offer a context-actions control with exactly two entries: Edit and Remove, always shown (Flows cannot be YAML-managed).

#### Scenario: Clicking a Flow row opens the preview panel
- **WHEN** a user clicks a row on the Flows list page
- **THEN** a right-side panel opens showing that Flow's summary (its home System and step count), and the list remains visible

#### Scenario: A fast second click on the open Flow row navigates to its detail page
- **WHEN** a user clicks a Flow row, the preview panel opens for it, and the user clicks that same row again within the double-click window
- **THEN** they are navigated to that Flow's detail page

#### Scenario: Flow row always shows Edit and Remove
- **WHEN** a user views a row in the Flows list table
- **THEN** its context-actions control offers exactly two entries: Edit and Remove
