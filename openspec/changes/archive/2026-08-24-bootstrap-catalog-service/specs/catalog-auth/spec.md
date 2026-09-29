## ADDED Requirements

### Requirement: Session login via allauth headless
A user SHALL be able to establish a session by submitting valid username/password credentials to the allauth headless login endpoint.

#### Scenario: Successful login persists a session
- **WHEN** valid credentials are submitted to the allauth headless login endpoint
- **THEN** a session is established and subsequent authenticated requests succeed without resubmitting credentials

### Requirement: Unauthenticated access is rejected
Any `/api/*` endpoint other than `_allauth/*` SHALL require an authenticated session.

#### Scenario: No session, request rejected
- **WHEN** any `/api/*` endpoint (other than `_allauth/*`) is called with no session
- **THEN** it returns 401 or redirects to login

### Requirement: Ownership-based edit permission
A user SHALL be able to edit a manual entity only if they are a member of that entity's `owner` Group, or a superuser; this rule SHALL apply uniformly across System, Component, Resource, and API.

#### Scenario: Owner-Group member can edit any of the four kinds
- **WHEN** a member of Group *G* attempts to edit a manual Component, Resource, or API owned by *G*
- **THEN** the request succeeds and the fields are updated

#### Scenario: Superuser can edit regardless of Group membership
- **WHEN** a superuser attempts to edit a manual entity owned by a Group they are not a member of
- **THEN** the request succeeds

### Requirement: Read access is unrestricted for any logged-in user
Any authenticated user SHALL be able to list and retrieve any System, Component, Resource, or API regardless of its `owner` Group, since v1 has no per-entity read ACL.

#### Scenario: Non-owner can read an entity they don't own
- **WHEN** a logged-in user who is not a member of Group *G* and not a superuser retrieves a System, Component, Resource, or API owned by *G*
- **THEN** the request succeeds with the entity's full data, since only writes are ownership-restricted
