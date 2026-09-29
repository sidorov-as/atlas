## MODIFIED Requirements

### Requirement: Flow belongs to exactly one home System
A Flow SHALL have a required, non-nullable reference to exactly one `System` (its home system). A Flow's `name` SHALL be unique within its home system. `name` SHALL be stripped of leading/trailing whitespace and SHALL be rejected if the stripped value is empty or contains `/` or `:`; a PATCH that omits `name` SHALL leave the existing name unchanged, but a PATCH that explicitly provides an invalid `name` SHALL be rejected the same as on create. Deleting a System that is the home system of one or more Flows SHALL be blocked until those Flows are deleted or reassigned.

#### Scenario: Flow created with a home system
- **WHEN** a Flow is created with a valid home `system` reference, a unique `name` within that system, and a `steps` array
- **THEN** the Flow is persisted and appears under that system

#### Scenario: Flow requires a home system
- **WHEN** a Flow is created without a `system` reference
- **THEN** the request is rejected

#### Scenario: Duplicate name within the same system is rejected
- **WHEN** a Flow is created with a `name` that already exists on another Flow whose home system is the same
- **THEN** the request is rejected

#### Scenario: Deleting a system with flows is blocked
- **WHEN** an attempt is made to delete a System that is the home system of at least one Flow
- **THEN** the deletion is rejected until those Flows are deleted or reassigned to a different home system

#### Scenario: Empty or whitespace-only name is rejected
- **WHEN** a Flow is created or updated with `name` set to `""` or `"   "`
- **THEN** the request is rejected and no Flow is created or modified

#### Scenario: Name containing a forbidden character is rejected
- **WHEN** a Flow is created or updated with `name` containing `/` or `:`
- **THEN** the request is rejected

#### Scenario: Omitting name on a PATCH leaves it unchanged
- **WHEN** an existing Flow is updated via PATCH without a `name` field in the request body
- **THEN** the Flow's existing `name` is unchanged
