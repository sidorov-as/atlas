## ADDED Requirements

### Requirement: Full Markdown documentation is authored separately from an entity summary
System, Component, Resource, API, and Flow SHALL each expose an optional `documentation` field containing Markdown, separate from their short `description` summary. Manual create and edit forms for those kinds SHALL provide a Gravity UI Markdown editor after all standard and kind-specific fields, and saving the form SHALL persist its Markdown value.

#### Scenario: User saves Markdown documentation for a Component
- **WHEN** a user creates or edits a manual Component and enters headings, lists, or links in the Documentation editor
- **THEN** the Component is saved with that Markdown in `metadata.documentation`, while its short `metadata.description` remains unchanged

#### Scenario: User saves Markdown documentation for a Flow
- **WHEN** a user creates or edits a Flow and enters Markdown in the Documentation editor
- **THEN** the Flow is saved with that Markdown in `documentation`, independently of its short `description` and `steps`

### Requirement: Full Markdown documentation is rendered in the detail experience
The Overview tab for System, Component, Resource, and API SHALL render `metadata.documentation` as formatted Markdown. A Flow detail page SHALL render its `documentation` as formatted Markdown below the graph and Steps section. Empty documentation SHALL use an explicit empty state rather than rendering the short summary a second time.

#### Scenario: API Overview renders full documentation
- **WHEN** a user opens an API whose `metadata.documentation` contains Markdown formatting
- **THEN** Overview renders the formatted documentation and does not use `metadata.description` as its body content

#### Scenario: Flow documentation follows graph and steps
- **WHEN** a user opens a Flow with steps and documentation
- **THEN** the graph and Steps appear before the formatted documentation section
