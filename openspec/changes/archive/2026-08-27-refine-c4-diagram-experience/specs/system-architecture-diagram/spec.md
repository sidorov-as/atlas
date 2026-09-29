## ADDED Requirements

### Requirement: System Architecture diagram exposes a System's internal catalog scope
The system SHALL generate a System Architecture diagram for a selected System containing that System's Components, APIs, and Resources, together with directly related external endpoints. It SHALL retain explicit Architecture Relationship metadata and use derived catalog relations only as fallback edges.

#### Scenario: System architecture includes internal elements
- **WHEN** a System contains Components, APIs, and Resources
- **THEN** its System Architecture diagram includes those elements without adding them to its System Context diagram

#### Scenario: Explicit interaction supersedes a derived edge
- **WHEN** visible endpoints have both a directed Architecture Relationship and a derived catalog relation
- **THEN** the System Architecture diagram renders the declared interaction and no duplicate generic derived edge

