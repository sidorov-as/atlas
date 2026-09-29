## ADDED Requirements

### Requirement: Flow content fields are size-bounded
A Flow's `description` and `documentation` SHALL each be bounded to a fixed maximum length, and its `steps` list SHALL be bounded to a fixed maximum number of entries.

#### Scenario: Oversized description or documentation is rejected
- **WHEN** a Flow is created or updated with `description` or `documentation` longer than its declared maximum length
- **THEN** the request is rejected with a validation error and no Flow is created or modified

#### Scenario: Too many steps is rejected
- **WHEN** a Flow is created or updated with more `steps` entries than the declared maximum
- **THEN** the request is rejected with a validation error and no Flow is created or modified
