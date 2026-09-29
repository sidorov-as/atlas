## ADDED Requirements

### Requirement: System detail distinguishes Context and System Architecture views
The System detail page SHALL expose separately named C4 System Context and System Architecture tabs, each rendered full width through the reusable diagram viewer.

#### Scenario: User opens System Architecture
- **WHEN** a user selects the System Architecture tab for a System
- **THEN** the viewer requests that System's `architecture` diagram endpoint rather than its context endpoint

### Requirement: Architecture Relationship target selection is searchable and typed
The create and edit form for an outgoing manual Architecture Relationship SHALL provide a searchable target-ref lookup limited to System, Component, API, Resource, User, and Group catalog records. It SHALL submit the selected canonical ref and display the target kind to the user.

#### Scenario: User selects an actor target
- **WHEN** an editor searches for a catalog User in the target lookup and selects it
- **THEN** the form submits that User's canonical ref as the Architecture Relationship target

