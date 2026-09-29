## MODIFIED Requirements

### Requirement: Add/Edit forms for manual entities only
A manual entity's detail page SHALL show Add/Edit affordances; a YAML-managed entity's detail page SHALL show a read-only banner naming the backing repository instead. The add/edit forms for manual System, Component, Resource, and API entities SHALL place their Save/Cancel actions in a header row (title left, actions right) matching the action-row layout of that entity's own detail page. System and Resource forms SHALL keep a single-column body with the Markdown Documentation editor after their standard and kind-specific fields. Component and API forms SHALL split their body into an Overview tab (standard and kind-specific fields) and a Documentation tab (the Markdown editor alone, not width-constrained by the fields column).

#### Scenario: YAML-managed entity shows a banner, not an Edit button
- **WHEN** a user opens the detail page of an entity ingested from `org/repo`
- **THEN** the page shows "managed by `catalog-info.yaml` in `org/repo`" instead of an Edit button

#### Scenario: Add/Edit form actions sit in a top header row
- **WHEN** a user opens the create or edit form for a manual System, Component, Resource, or API
- **THEN** Save (or Create) and Cancel render in a header row above the form body, title on the left and the buttons on the right, matching the action-row layout used by that entity kind's own detail page

#### Scenario: System and Resource forms keep Documentation after their fields
- **WHEN** a user opens the create or edit form for a manual System or Resource
- **THEN** the Markdown Documentation editor follows its standard and kind-specific fields in the same single-column body, with no separate tab

#### Scenario: Component and API forms separate fields from Documentation
- **WHEN** a user opens the create or edit form for a manual Component or API
- **THEN** its Name, Title, Description, Tags, and kind-specific fields render under an Overview tab, and the Markdown Documentation editor renders alone under a separate Documentation tab that is not constrained to the fields column's width
