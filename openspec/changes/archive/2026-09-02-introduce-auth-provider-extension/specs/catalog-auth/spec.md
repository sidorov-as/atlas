## MODIFIED Requirements

### Requirement: Session login via the selected default provider
A user SHALL be able to establish a session by authenticating via the deployment's default authentication provider. For the official distribution with `atlas.auth.local` as the only or default provider, this SHALL be the existing allauth-headless username/password flow, unchanged.

#### Scenario: Successful local login persists a session
- **WHEN** valid credentials are submitted to the `atlas.auth.local` provider's login endpoint
- **THEN** a session is established and subsequent authenticated requests succeed without resubmitting credentials

### Requirement: Ownership-based edit permission
A user SHALL be able to edit a manual entity only if they are a member of that entity's `owner` Group, or a superuser; this rule SHALL apply uniformly across every Entity Kind and SHALL be enforced by the built-in RBAC `PolicyEvaluator`, not by kind-specific view logic.

#### Scenario: Owner-Group member can edit any registered kind
- **WHEN** a member of Group *G* attempts to edit a manual entity of any registered kind owned by *G*
- **THEN** the request succeeds and the fields are updated

#### Scenario: Superuser can edit regardless of Group membership
- **WHEN** a superuser attempts to edit a manual entity owned by a Group they are not a member of
- **THEN** the request succeeds
