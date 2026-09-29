## ADDED Requirements

### Requirement: Authentication documentation begins with a selection guide
Operating Atlas SHALL provide an authentication overview that compares local credentials, standards-based OIDC, supported provider-specific OAuth2, and custom providers. It SHALL distinguish browser SSO from API bearer-token authorization, identify unsupported SAML/API-token behavior, and direct readers to the appropriate runnable example and task guide.

#### Scenario: Operator chooses corporate SSO
- **WHEN** an operator has Keycloak, Okta, Entra ID, Auth0, or another standards-compliant OIDC service
- **THEN** the selection guide recommends OIDC and links to discovery, client registration, callback, provisioning, group-sync, and verification guidance

#### Scenario: Operator asks for generic OAuth
- **WHEN** an operator wants GitHub, GitLab, Gitea, or another OAuth2 service
- **THEN** the guide explains that identity and groups are provider-specific and lists only adapters Atlas actually supports

#### Scenario: Operator wants API tokens
- **WHEN** a reader needs machine-to-machine bearer authentication
- **THEN** the guide states that browser authentication providers establish Atlas sessions and does not claim they enable API bearer-token authentication

### Requirement: Authentication guides explain identity and authorization lifecycle
Concept and operator documentation SHALL explain External Identity, Principal, Actor, Group/Team, owner Group, staff/superuser status, Purge Grant, provider-managed membership, and session as distinct concepts. Each provider guide SHALL state exactly when each object is created, linked, updated, removed, or left manual.

#### Scenario: SSO user can log in but cannot edit
- **WHEN** an operator investigates an authenticated user without ownership access
- **THEN** documentation leads them through Principal provisioning, Actor linking, Group mapping, owner membership, and PolicyEvaluator behavior

#### Scenario: External group is removed
- **WHEN** an operator chooses additive or exact reconciliation
- **THEN** documentation explains whether and when Atlas membership is removed and which manual memberships are preserved

### Requirement: Every supported provider has a complete task guide
Local, OIDC, and each supported provider-specific OAuth2 implementation SHALL have a task-oriented guide covering prerequisites, manifest selection/defaulting, typed configuration, secret injection, public origins, provider-side registration, callbacks, scopes/claims, provisioning, group synchronization, logout, fallback access, verification, failure symptoms, security limitations, and links to its example.

#### Scenario: Operator configures OIDC from documentation
- **WHEN** the operator follows the OIDC guide
- **THEN** they register the documented exact callback, use a discovery URL and secret reference, authenticate a user, and verify expected and denied permissions

#### Scenario: Provider lacks remote logout
- **WHEN** a supported provider ends only the Atlas session
- **THEN** its guide clearly states that the upstream provider session remains active

### Requirement: Plugin authors can implement a custom authentication provider
Plugin Development SHALL document the public provider SDK, flow-kind choice, two-phase descriptor/runtime lifecycle, typed configuration and secrets, normalized identity contract, provisioning handoff, route and frontend behavior, failure sanitization, health, compatibility, packaging, and contract tests. It SHALL include a runnable minimal custom credential tutorial and a separate LDAP implementation mapping with protocol-specific security obligations; shipping a production LDAP plugin or OpenLDAP topology is outside this change.

#### Scenario: Author implements a custom credential provider
- **WHEN** a plugin author follows the custom provider tutorial
- **THEN** they build and select a separately packaged fixture provider using public Plugin API imports, run contract/import-boundary tests, and can identify how its inputs/results map to a future LDAP implementation

#### Scenario: Author considers a custom frontend
- **WHEN** a provider fits the standard credential or redirect flow
- **THEN** documentation directs the author to provider presentation metadata rather than a provider-owned login page and identifies multi-step custom UI as outside the v1 contract

### Requirement: Authentication documentation and examples are source-validated
Documentation CI SHALL validate authentication navigation, links, manifest/config snippets, callback paths, environment-variable references, provider ids, and Compose examples against current source contracts. Security-sensitive examples SHALL be scanned for non-disposable secrets and claims of unsupported production behavior.

#### Scenario: Callback route changes
- **WHEN** implementation changes a supported callback route without updating guides and examples
- **THEN** documentation/example validation fails

#### Scenario: Provider config field is renamed
- **WHEN** a guide or example uses a field no longer accepted by the provider schema
- **THEN** validation fails before publication

### Requirement: Authentication troubleshooting is symptom-oriented and secret-safe
Troubleshooting SHALL cover hidden/missing providers, composition failures, signup rejection, local login disabled, callback mismatch, discovery/issuer failure, CSRF/origin errors, provider outage, link collision, provisioning rejection, missing Actor, stale/exact group behavior, and logout expectations without instructing readers to print credentials, tokens, raw claims, or secrets.

#### Scenario: Login succeeds but access is missing
- **WHEN** a reader selects that symptom
- **THEN** the guide distinguishes authentication, Principal/Actor provisioning, group reconciliation, ownership, and authorization checks in a safe diagnostic sequence


### Requirement: Operators can verify migration and revocation boundaries
Guides SHALL document source namespace changes, operator identity-link creation/revocation/restoration, privileged-target confirmation, legacy grant classification, expired exact grants, additive retention, session expiry and revoke-all, inactive Principals, restricted eligibility trust, and explicit admin break-glass behavior including catalog access from admin sessions. The guides SHALL distinguish bounded login-time synchronization from immediate IdP deprovisioning, which v1 does not provide. Recovery, outbound trust, password defaults, proxy configuration, and token/log retention SHALL have source-validated configuration references and negative verification steps.

#### Scenario: Operator enables exact sync on a legacy installation
- **WHEN** the operator follows the migration guide
- **THEN** they inspect and classify or acknowledge legacy manual grants and verify that removing a transferred provider grant removes access without deleting independent manual access

#### Scenario: Operator disables access urgently
- **WHEN** an upstream account is removed but its Atlas session remains live
- **THEN** the guide provides an immediate local block/revoke procedure and explains the configured maximum delay without that procedure

### Requirement: Authentication guides explain existing read-only account integration
Operator and provider-author guides SHALL reference the read-only account contract rather than define a provider-specific role. They SHALL explain preservation across login/linking/group sync, live-session flag changes, admin break-glass restrictions, and the pre-created flagged Principal plus exact link plus preprovisioned first-access workflow. Troubleshooting SHALL distinguish a valid session with a read-only denial from missing memberships, expired grants, and failed authentication.

#### Scenario: Operator issues external read-only access
- **WHEN** an operator follows the provisioning guide
- **THEN** the guide prepares the flagged account before enabling its identity and verifies read success and write denial on the first external login

#### Scenario: Group membership exists but writes are denied
- **WHEN** a read-only Principal has an effective owner-group grant
- **THEN** troubleshooting identifies the independent account restriction without recommending provider remapping or break-glass as a bypass
