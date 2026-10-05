## Purpose

Flows as searchable documents, found by name, description, documentation and step text, authorized by the flow read rules and owning-system access.

## Requirements

### Requirement: Flows are searchable
The flows plugin SHALL register a search source that produces one document per flow, with the flow's name as title and its description, documentation and the visible text of its steps as body. The visible text of a step SHALL include its title, summary and external label where present.

#### Scenario: Found by name
- **WHEN** a user searches for part of a flow's name
- **THEN** the flow appears in results

#### Scenario: Found by documentation
- **WHEN** a user searches for a phrase present only in a flow's documentation
- **THEN** the flow appears with a snippet around the phrase

#### Scenario: Found by step text
- **WHEN** a user searches for text that appears only in a step's external label
- **THEN** the flow appears in results

### Requirement: A flow hit opens the flow
A flow result SHALL link to the flow's detail page in its owning system. A match inside step text SHALL lead to the whole flow rather than a specific step.

#### Scenario: Open a flow from search
- **WHEN** the user opens a flow result
- **THEN** the application navigates to that flow

### Requirement: Flow results follow existing flow read rules
`resolve` SHALL return only flows the requesting actor may read under the flows plugin's current read rules, and SHALL omit flows whose owning system is not accessible.

#### Scenario: Actor cannot see the owning system
- **WHEN** the actor cannot read a flow's owning system
- **THEN** that flow is omitted from results

#### Scenario: Flow deleted after indexing
- **WHEN** a flow was deleted but is still in the index
- **THEN** it is omitted from results

### Requirement: Flow changes reach the index
Creating, updating or deleting a flow SHALL record a pending change, and renaming or removing its owning system SHALL cause its flows' documents to be refreshed or removed.

#### Scenario: Flow renamed
- **WHEN** a flow is renamed
- **THEN** a search for the new name finds it after the next indexing run and the old name no longer does

#### Scenario: Owning system removed
- **WHEN** a flow's owning system is removed
- **THEN** the flow no longer appears in results after the next indexing run

### Requirement: Steps without text do not break indexing
A flow whose steps are empty, malformed or contain no text SHALL still be indexed by its own fields.

#### Scenario: Empty steps
- **WHEN** a flow has no steps
- **THEN** it is indexed from its name, description and documentation
