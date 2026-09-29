## ADDED Requirements

### Requirement: Explicit User and Group interactions are represented as C4 People
The system SHALL allow catalog User and Group entities as Architecture Relationship endpoints. A System Context diagram SHALL render an explicitly related User or Group as a C4 Person, while ownership alone SHALL not render a Person.

#### Scenario: Explicit user interaction appears as a person
- **WHEN** a catalog User has an explicit Architecture Relationship to a System or Component in the selected System's context
- **THEN** the System Context diagram includes that User as a Person and renders the declared interaction

### Requirement: Booking demo demonstrates actor architecture interactions
The booking demo seed SHALL create representative Architecture Relationships for synchronous, asynchronous, data-access, manual, and external interactions, including at least one explicit User or Group actor interaction.

#### Scenario: Seeded context shows a person
- **WHEN** an operator seeds the booking demo and opens the relevant System Context diagram
- **THEN** it includes the seeded actor as a Person and its explicit interaction
