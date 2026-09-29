## MODIFIED Requirements

### Requirement: Session login via the selected default provider
A user SHALL be able to establish a Core-managed session through any selected authentication provider. The deployment's default provider SHALL determine the first login interaction, while every other selected provider remains reachable through provider choice. A local username/password form SHALL be shown and accepted only when `atlas.auth.local` is selected.

#### Scenario: Successful local login persists a session
- **WHEN** valid credentials are submitted to `atlas.auth.local` in a deployment that selected it
- **THEN** a Core-managed session is established and subsequent authenticated requests succeed without resubmitting credentials

#### Scenario: Successful external login persists the same session type
- **WHEN** a selected redirect or custom credential provider returns a verified identity that passes provisioning
- **THEN** Core establishes the same Django session type used by local login and protected APIs do not need to know the provider

#### Scenario: Direct local login when local is unselected
- **WHEN** valid Django credentials are posted directly to the local login operation but `atlas.auth.local` is absent from `auth.providers`
- **THEN** authentication is rejected and no Atlas session is created

## ADDED Requirements

### Requirement: Local self-signup is closed by default
Atlas SHALL reject anonymous local-account signup by default through a server-side account policy. Hiding the signup operation in the UI or documentation SHALL NOT satisfy this requirement. A deployment MAY explicitly opt into local self-signup, and that opt-in SHALL be represented in authoritative deployment configuration.

#### Scenario: Default deployment receives signup request
- **WHEN** an anonymous caller posts otherwise valid local signup data without an explicit signup opt-in
- **THEN** the server returns a signup-closed response and creates no User, Actor, ExternalIdentityLink, or session

#### Scenario: Signup endpoint is called outside the UI
- **WHEN** a caller invokes the underlying headless signup operation directly
- **THEN** the same server-side signup policy rejects the request

#### Scenario: Deployment explicitly enables signup
- **WHEN** an operator selects local auth and explicitly enables local self-signup
- **THEN** signup follows allauth validation and Core provisioning policy and the public configuration accurately reports that signup is open

### Requirement: Local account bootstrap is controlled and documented
A deployment using local authentication SHALL provide a documented operator-controlled way to create or recover the first administrative account without enabling anonymous signup or storing a production password in source control.

#### Scenario: Operator bootstraps first administrator
- **WHEN** an authorized operator runs the supported bootstrap procedure with secret input
- **THEN** exactly the intended administrative account is created or updated and the secret is not written to repository files or logs

### Requirement: Authentication endpoints do not weaken API session policy
Provider discovery, provider start/callback, credential login, signup policy responses, session inspection, and logout MAY be available without an existing session as required by their flow. All catalog `/api/*` operations SHALL continue to require a valid Core-managed authenticated session unless a separate specification explicitly declares them public.

#### Scenario: External callback completes
- **WHEN** a callback verifies successfully and provisioning completes
- **THEN** subsequent catalog API requests authenticate through the new Core-managed session cookie

#### Scenario: Bearer token is presented to a catalog API
- **WHEN** a caller presents only an upstream OIDC/OAuth access token without a Django session
- **THEN** the catalog API rejects it unless a future separately specified API-token capability is selected


### Requirement: Session validity is bounded and revocable
Core SHALL enforce a finite absolute session age, defaulting to eight hours, without extending it through API activity. Session metadata SHALL record the establishing provider, source, identity link where applicable, authentication time, and a Principal revocation generation. Before session establishment and on every authenticated request, Core SHALL reject inactive/blocked Principals, stale revocation generations, revoked identity links, removed providers/sources, expired sessions, and admin break-glass sessions whose explicit policy or Principal allowlist authorization has been withdrawn. Shortening configured maximum age SHALL apply to existing sessions from their authentication time. Revocation SHALL survive reactivation/reselection, and in-flight verification SHALL not bypass a later revocation. This validation SHALL apply uniformly to Core APIs, plugin APIs, compatibility endpoints, and Django admin. Metadata SHALL govern authentication validity only and SHALL NOT grant permissions.

#### Scenario: Principal is blocked with an active session
- **WHEN** an operator blocks a Principal or invokes the supported revoke-all-sessions command
- **THEN** existing sessions fail on the next request and an in-flight login using an older revocation generation cannot create a valid session

#### Scenario: Provider is deselected
- **WHEN** a deployment removes the provider/source that established an existing session
- **THEN** that session is rejected under the new configuration even if its cookie has not expired

#### Scenario: Upstream user is removed
- **WHEN** an IdP removes a user but sends no notification to Atlas
- **THEN** Atlas does not claim immediate detection, the existing session lasts no longer than its absolute age, and renewal requires a new successful provider verification

### Requirement: Admin password recovery requires explicit policy
Django admin password login SHALL default to disabled independently of catalog local-provider selection. A deployment MAY explicitly enable `adminPasswordLogin=break-glass` with a non-empty allowlist of pre-existing administrative Principal ids. Only active staff accounts in that allowlist SHALL be accepted by this password path. The official local distribution SHALL explicitly document its bootstrap/allowlist procedure. Existing valid catalog sessions MAY access admin according to normal staff permissions. Break-glass password sessions SHALL use Core session validity, CSRF, rate limiting, and audit rules and SHALL be explicitly documented as also usable for catalog APIs; there is no implicit admin-only isolation.

#### Scenario: SSO-only deployment has no admin password opt-in
- **WHEN** a user posts valid local staff credentials to Django admin while admin password recovery is disabled
- **THEN** no session is established and catalog APIs remain inaccessible through that attempt

#### Scenario: Explicit break-glass account signs in
- **WHEN** an allowlisted active staff Principal authenticates under the explicit break-glass policy
- **THEN** a bounded audited Core session is created that can access catalog APIs according to ordinary authorization

#### Scenario: Unlisted staff account attempts recovery login
- **WHEN** a staff account outside the configured allowlist submits a valid password to admin
- **THEN** the password path rejects it without revealing whether the account exists

### Requirement: Browser authentication uses protected cookies and origins
Production session cookies SHALL be Secure and HttpOnly with an explicit SameSite policy compatible with supported callbacks (Lax for v1 top-level GET callbacks). CSRF cookies SHALL be Secure; the documented SPA-readable CSRF cookie need not be HttpOnly. Credential login, signup, redirect start, logout, and account mutations SHALL enforce CSRF and trusted-origin checks even before authentication. Successful login SHALL rotate the session identifier. Callback/public URLs SHALL derive from an operator-configured public origin, with forwarded headers trusted only from configured proxies. Return URLs SHALL reject foreign origins, scheme-relative URLs, credentials in URLs, and ambiguous encodings. Authentication/session responses SHALL be non-cacheable and callback pages SHALL not leak codes via referrers or third-party resources.

#### Scenario: Login is submitted cross-site
- **WHEN** a credential, signup, start, or logout request lacks valid CSRF/origin proof
- **THEN** Core rejects it without performing the requested state change

#### Scenario: Attacker supplies a pre-login session id or Host header
- **WHEN** successful authentication follows an attacker-known session id or an untrusted forwarded host
- **THEN** the old session id does not authenticate and generated callback URLs retain the configured public origin

### Requirement: Local passwords and recovery share a security policy
Local signup, bootstrap, password change, and reset SHALL enforce a documented password policy, including a default minimum of fifteen characters, common-password and user-similarity rejection, support for at least sixty-four characters, and no silent truncation. Recovery SHALL default to operator-managed; anonymous password-reset routes SHALL remain unavailable until a separately explicit configuration provides verified recovery addresses, a working mail transport, expiring single-use tokens, generic responses, and throttling. Upstream profile email changes SHALL NOT silently change verified recovery destinations. Password resets and security-sensitive credential changes SHALL revoke existing sessions.

#### Scenario: Signup opt-in encounters a weak password
- **WHEN** local signup is enabled and the submitted password fails policy
- **THEN** registration is rejected despite any permissive framework defaults

#### Scenario: Recovery is not configured
- **WHEN** a caller directly invokes an underlying framework password-reset endpoint
- **THEN** it cannot send a reset or establish/change credentials through an undocumented recovery path

### Requirement: Authentication integration preserves Core read-only enforcement
Every authentication provider, Atlas gateway path, compatibility alias and admin break-glass session SHALL preserve the mandatory Core read-only authorization restriction defined by the read-only account capability. Successful authentication SHALL not bypass the guarded evaluator, independent mutation guards, admin restrictions, or job authorization. Read-only login/logout and Core-owned provisioning SHALL remain available under their existing service-operation policies without permitting AccountAccess mutation.

#### Scenario: Read-only account authenticates through a selected provider
- **WHEN** a read-only Principal completes local, OIDC, Gitea, or custom credential authentication
- **THEN** normal permitted reads succeed and a subsequent user mutation is rejected before effects regardless of membership or privilege

#### Scenario: Read-only administrator uses break-glass
- **WHEN** an allowlisted read-only staff or superuser authenticates through the explicit admin password policy
- **THEN** the session cannot mutate admin/catalog state or remove its own restriction

### Requirement: Authentication frontend preserves current read-only presentation
The gateway and frontend session refactor SHALL retain `/api/me/`'s current isReadOnly signal and the refresh/loading/error behavior defined for read-only accounts. Provider session data SHALL not replace this signal with a cached authentication-time value. Flag changes SHALL affect subsequent authorization checks in existing external sessions without requiring reauthentication; clearing the flag SHALL restore ordinary authorization only.

#### Scenario: Redirect login populates access state
- **WHEN** a read-only Principal returns from a successful external callback
- **THEN** the frontend loads current isReadOnly before presenting write affordances and retains normal read navigation

#### Scenario: Operator restricts an active external session
- **WHEN** an operator sets read_only while an OIDC or OAuth session is active
- **THEN** the next write authorization is denied even if the UI is stale, and the frontend refreshes on its established access-state refresh triggers

#### Scenario: Operator clears the flag in an active external session
- **WHEN** read_only is cleared for a logged-in external Principal
- **THEN** subsequent writes still require ordinary evaluator permissions and the frontend refreshes the current flag
