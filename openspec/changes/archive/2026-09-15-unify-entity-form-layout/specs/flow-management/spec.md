## ADDED Requirements

### Requirement: Flow create/edit form shares the standard entity-form header actions
The Flow create/edit form SHALL place its Save/Cancel actions in the same top header row (title left, actions right) used by System/Component/Resource/API Add/Edit forms and by the Flow detail page's own Edit/Delete actions, instead of a dedicated row under the title. The General/Flow tab structure and the General tab's side-by-side fields/Documentation layout SHALL remain unchanged.

#### Scenario: Flow form actions sit in the shared header row
- **WHEN** a user opens the create or edit form for a Flow
- **THEN** Save (or Create) and Cancel render in a header row above the General/Flow tabs, title on the left and the buttons on the right

#### Scenario: Flow tab actions are not duplicated in the Steps toolbar
- **WHEN** a user is on the Flow tab editing steps
- **THEN** Save and Cancel are not repeated next to the "Add Step" toolbar button — the header row above the tabs remains the only Save/Cancel control
