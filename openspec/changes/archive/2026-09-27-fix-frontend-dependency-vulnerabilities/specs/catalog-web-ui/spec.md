## MODIFIED Requirements

### Requirement: Login page
An unauthenticated user SHALL be directed to a Login page backed by allauth headless. The credential-provider submit control's accessible name SHALL reflect whether the deployment offers exactly one credential provider (`Sign in`) or more than one (`Sign in with {provider.displayName}`).

#### Scenario: Unauthenticated visit redirects to login
- **WHEN** a user with no session opens any catalog page
- **THEN** they are redirected to the Login page

#### Scenario: Single local credential provider submit button
- **WHEN** a deployment offers exactly one credential provider and a user submits the login form
- **THEN** the submit control's accessible name is `Sign in`
