## MODIFIED Requirements

### Requirement: Authentication Core is provider-agnostic
Authentication Core SHALL own Principal resolution orchestration, external identity linking, provisioning, session lifecycle, logout, return-URL validation, CSRF/security policy, and authorization handoff independently of which selected authentication provider verified the user. Providers SHALL return normalized verified identities and SHALL NOT establish parallel sessions or authorization systems.

#### Scenario: Session behavior is identical regardless of provider
- **WHEN** a session is established via any selected local, OIDC, provider-specific OAuth2, or third-party provider
- **THEN** its Atlas session lifecycle, CSRF policy, API authentication, and local logout behavior are identical to a session established via any other selected provider

#### Scenario: Provider returns authorization-looking attributes
- **WHEN** a selected provider verifies an identity carrying roles, claims, teams, groups, or administrative-looking attributes
- **THEN** Authentication Core passes only configured normalized membership inputs to provisioning and authorization remains governed by the shared PolicyEvaluator

### Requirement: A deployment selects one or more providers and a default
A deployment SHALL select one or more registered authentication provider ids through the distribution manifest and SHALL designate exactly one selected provider as the default. Only selected providers SHALL be usable at runtime; the default SHALL determine the initial login interaction but SHALL NOT disable other selected providers.

#### Scenario: Local and OIDC selected together
- **WHEN** a deployment selects both `atlas.auth.local` and `atlas.auth.oidc` with `atlas.auth.oidc` as default
- **THEN** unauthenticated visitors are directed to OIDC first and can reach an explicit provider-choice path offering local break-glass login

#### Scenario: OIDC-only deployment
- **WHEN** a deployment selects only `atlas.auth.oidc`
- **THEN** the local credential form and catalog local login/signup operations are unavailable while OIDC start/callback behavior is available; admin password login is also disabled unless separately opted into as an explicit break-glass exception

#### Scenario: Default is not selected
- **WHEN** a manifest names an auth default absent from its auth providers
- **THEN** composition fails before runtime generation

#### Scenario: Installed provider is not selected
- **WHEN** a provider implementation is present in the image but absent from `auth.providers`
- **THEN** it is omitted from provider discovery and direct invocation is rejected

### Requirement: External identities map to a stable principal
Every successful external authentication SHALL resolve through a provider/source-scoped stable subject to one stable Atlas Principal according to the configured provisioning policy; mutable usernames, emails, display names, claims, directory membership, and OAuth scopes SHALL NOT silently change that identity mapping.

#### Scenario: Repeated OIDC login resolves to the same principal
- **WHEN** the same OIDC issuer, provider id, and subject log in on two separate occasions
- **THEN** both sessions are associated with the same Atlas Principal even if mutable profile claims changed

#### Scenario: Link collision occurs
- **WHEN** a verified provider identity is already linked to another Principal
- **THEN** login fails with an auditable conflict and the existing mapping is not reassigned

### Requirement: Authentication claims do not directly grant authorization
Claims, directory attributes, OAuth scopes, groups, or roles returned by an authentication provider SHALL NOT be interpreted as direct authorization decisions. They MAY inform Core-controlled profile provisioning or ordinary Group membership through explicit mapping and reconciliation policy, but SHALL NOT set staff/superuser flags, create Purge Grants, or bypass the PolicyEvaluator.

#### Scenario: An OIDC claim does not bypass permission checks
- **WHEN** a user authenticates via OIDC with claims indicating elevated status
- **THEN** their access is governed entirely by the Authorization Service against the resulting ordinary Atlas state, not by inspecting the claim during permission evaluation

#### Scenario: OAuth scope resembles a permission
- **WHEN** a provider returns an OAuth scope whose name resembles an Atlas permission
- **THEN** the scope grants no Atlas permission unless separate Core-managed provisioning creates ordinary state that the PolicyEvaluator recognizes

## ADDED Requirements

### Requirement: Provider routes follow selected flow capabilities
Core SHALL expose credential operations only for selected credential providers and start/callback operations only for selected redirect providers. Provider route availability SHALL depend on selection and declared flow kind, not on whether that provider is the default.

#### Scenario: Non-default redirect provider is selected
- **WHEN** a redirect provider is selected but another provider is default
- **THEN** its start and callback routes remain available from the provider-choice interaction

#### Scenario: No redirect provider is selected
- **WHEN** every selected provider uses credentials
- **THEN** no external callback route is published as an active authentication option

### Requirement: Default-provider redirect has a safe fallback
When the default provider uses redirect flow, the login experience SHALL direct a first-time unauthenticated visit to that provider while retaining a non-looping, explicit provider-choice path. Authentication failure or provider unavailability SHALL offer that path whenever another provider is selected.

#### Scenario: Default redirect provider fails
- **WHEN** the default redirect provider returns an error and local fallback is selected
- **THEN** the user can reach the provider-choice page and submit local credentials without being immediately redirected again

#### Scenario: User explicitly requests provider choice
- **WHEN** an unauthenticated user opens the documented provider-choice URL
- **THEN** all selected providers are presented and no automatic redirect occurs

