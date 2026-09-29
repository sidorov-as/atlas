## ADDED Requirements

### Requirement: Reproducible full application runtime
The project SHALL provide documented Docker Compose workflows that build and
start the backend with its PostgreSQL dependency, ingestion worker, and
frontend in both source-mounted development and immutable production-like
modes.

#### Scenario: Production backend starts after schema initialization
- **WHEN** the production Compose workflow is started against an empty
  PostgreSQL volume
- **THEN** the backend begins serving only after migrations complete

#### Scenario: Development backend starts from mounted source
- **WHEN** a developer starts the documented development Compose workflow
- **THEN** the backend uses the mounted source directory and reaches its
  PostgreSQL service by the Compose hostname
