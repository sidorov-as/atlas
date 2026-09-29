## ADDED Requirements

### Requirement: Authentication Core is provider-agnostic
Authentication Core SHALL own principal identity, session lifecycle, logout, and CSRF/security policy independent of which authentication provider established the session.

#### Scenario: Session behavior is identical regardless of provider
- **WHEN** a session is established via any selected authentication provider
- **THEN** its session lifecycle, CSRF policy, and logout behavior are identical to a session established via any other selected provider

### Requirement: A deployment selects one or more providers and a default
A deployment SHALL be able to select multiple authentication providers and designate one as the default.

#### Scenario: Local and OIDC selected together
- **WHEN** a deployment selects both `atlas.auth.local` and `atlas.auth.oidc` with `atlas.auth.oidc` as default
- **THEN** a user can authenticate via either provider, and unauthenticated visitors are directed to the default provider first

### Requirement: External identities map to a stable principal
An authentication provider SHALL resolve a successful external authentication to a stable Atlas principal; the same external identity SHALL always resolve to the same principal.

#### Scenario: Repeated OIDC login resolves to the same principal
- **WHEN** the same OIDC subject logs in on two separate occasions
- **THEN** both sessions are associated with the same Atlas principal

### Requirement: Authentication claims do not directly grant authorization
Claims or attributes returned by an authentication provider SHALL NOT be interpreted as authorization decisions; they SHALL only inform principal identity and, where a claims mapping is configured, group membership.

#### Scenario: An OIDC claim does not bypass permission checks
- **WHEN** a user authenticates via OIDC with claims indicating elevated status
- **THEN** their access is still governed entirely by the Authorization Service's permission checks against their resolved Group memberships, not by inspecting the claims directly
