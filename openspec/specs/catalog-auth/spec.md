# catalog-auth Specification

## Purpose
Session-based authentication for the catalog via django-allauth headless (local accounts only), and the ownership-based edit permission rule that governs writes to manual entities across System, Component, Resource, and API.

## Requirements

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

### Requirement: Unauthenticated access is rejected
Any `/api/*` endpoint other than `_allauth/*` SHALL require an authenticated session.

#### Scenario: No session, request rejected
- **WHEN** any `/api/*` endpoint (other than `_allauth/*`) is called with no session
- **THEN** it returns 401 or redirects to login

### Requirement: Ownership-based edit permission
A user SHALL be able to edit, remove, or revive a manual entity only if they are a member of that entity's `owner` Group, or a superuser; this rule SHALL apply uniformly across every Entity Kind and SHALL be enforced by the built-in RBAC `PolicyEvaluator`, not by kind-specific view logic. Purge SHALL instead require a Purge Grant (or global-admin status), not merely owner-Group membership.

#### Scenario: Owner-Group member can edit any registered kind
- **WHEN** a member of Group *G* attempts to edit a manual entity of any registered kind owned by *G*
- **THEN** the request succeeds and the fields are updated

#### Scenario: Superuser can edit regardless of Group membership
- **WHEN** a superuser attempts to edit a manual entity owned by a Group they are not a member of
- **THEN** the request succeeds

#### Scenario: Owner-Group member can remove and revive a manual entity
- **WHEN** a member of Group *G* invokes Remove, and later Revive, on a manual entity owned by *G*
- **THEN** both actions succeed under the same ownership-based permission that governs editing

#### Scenario: Owner-Group membership alone does not authorize Purge
- **WHEN** a member of Group *G* who holds no Purge Grant attempts to Purge a `removed` entity owned by *G*
- **THEN** the request is rejected — owner-Group membership authorizes edit/remove/revive, but Purge requires its own grant

### Requirement: Purge Grant permission, scoped per owner-Group with a global-admin override
Purging a `removed` entity SHALL require a `Purge Grant`: a permission a Group's own admins can assign to specific members, scoped to entities owned by that Group, or global-admin status which authorizes Purge on any entity regardless of grant or `source_kind`. This permission SHALL be enforced by the built-in RBAC `PolicyEvaluator`, the same mechanism enforcing ownership-based edit permission, not by kind-specific view logic.

#### Scenario: Owner-Group admin grants Purge rights to a member
- **WHEN** an admin of Group *G* assigns a Purge Grant scoped to *G* to a member of *G*
- **THEN** that member can subsequently invoke Purge on any `removed` entity owned by *G*

#### Scenario: Purge Grant does not authorize edits or remove/revive
- **WHEN** a user holding only a Purge Grant (and not owner-Group membership) attempts to edit, remove, or revive an active or removed entity owned by that Group
- **THEN** the edit/remove/revive request is rejected — Purge Grant authorizes Purge specifically, not the full set of write actions

#### Scenario: Global admin needs no Purge Grant
- **WHEN** a global admin invokes Purge on a `removed` entity owned by a Group they have no grant for
- **THEN** the purge is authorized

### Requirement: Removing an owning Group or Actor is blocked while it still owns active entities
A Group or Actor that still owns one or more `active` System, Component, Resource, or API SHALL NOT be deletable; `owner` SHALL be treated as a protected reference, checked the same way any other dependency is checked before a delete is allowed. An owner that only owns `removed` entities MAY be deleted.

#### Scenario: Deleting a Group with active owned entities is blocked
- **WHEN** an operator attempts to delete a Group that is the `owner` of at least one `active` Component
- **THEN** the deletion is rejected, naming the active entities still owned by that Group

#### Scenario: Deleting a Group whose owned entities are all removed succeeds
- **WHEN** every entity a Group owns has status `removed`, and an operator attempts to delete that Group
- **THEN** the deletion succeeds

#### Scenario: No entity is left displaying a nonexistent owner
- **WHEN** an owner-deletion attempt is blocked by this rule
- **THEN** no active entity is left referencing a Group or Actor that no longer exists

### Requirement: Read access is unrestricted for any logged-in user
Any authenticated user SHALL be able to list and retrieve any System, Component, Resource, or API regardless of its `owner` Group, since v1 has no per-entity read ACL.

#### Scenario: Non-owner can read an entity they don't own
- **WHEN** a logged-in user who is not a member of Group *G* and not a superuser retrieves a System, Component, Resource, or API owned by *G*
- **THEN** the request succeeds with the entity's full data, since only writes are ownership-restricted

### Requirement: Read-only Principal override
A Principal flagged `read_only` SHALL be denied every write permission — create, edit, remove, revive, and purge — on every entity of every Entity Kind, regardless of Group membership, ownership, holding a Purge Grant, or superuser status. This override SHALL be checked ahead of every other write rule (ownership-based edit permission, Purge Grant, global-admin status). Read access SHALL be entirely unaffected: a read-only Principal reads exactly as any other authenticated Principal does.

The flag SHALL normally be managed through Django admin by an authorized non-read-only operator. A Principal SHALL be allowed to read its own flag through `/api/me/` but SHALL NOT change it through a public self-service endpoint. An audited infrastructure recovery command SHALL be the only additional operator management path in this change.

#### Scenario: Read-only Group member cannot edit their own Group's entity
- **WHEN** a Principal flagged `read_only` who is a member of Group *G* attempts to edit a manual entity owned by *G*
- **THEN** the request is rejected, even though plain Group membership would otherwise authorize it

#### Scenario: Read-only Group member cannot create an entity in their own Group
- **WHEN** a Principal flagged `read_only` who is a member of Group *G* attempts to create a new entity owned by *G*
- **THEN** the request is rejected

#### Scenario: Read-only superuser cannot write
- **WHEN** a Principal flagged `read_only` who also holds `is_superuser` status attempts to edit, create, remove, revive, or purge any entity
- **THEN** every such request is rejected

#### Scenario: Read-only Purge Grant holder cannot purge
- **WHEN** a Principal flagged `read_only` who holds a Purge Grant for Group *G* attempts to purge a `removed` entity owned by *G*
- **THEN** the request is rejected

#### Scenario: Read-only Principal reads normally
- **WHEN** a Principal flagged `read_only` lists or retrieves any entity
- **THEN** the request succeeds exactly as it would for a non-read-only authenticated Principal

### Requirement: Read-only covers all user-initiated mutation surfaces
Core SHALL deny read-only user operations that change catalog data, relationships, tags, settings, access controls, or plugin state, including adopt, custom actions, and requests that enqueue mutating work. This requirement SHALL apply to direct APIs, services acting for the caller, and Django admin, regardless of staff/superuser status or selected evaluator. Denial SHALL occur before persistence, external side effects, or job enqueueing and SHALL return HTTP 403 for authenticated HTTP mutation attempts. Read permissions SHALL remain subject to their existing rules and SHALL NOT be expanded by read-only status.

#### Scenario: Read-only superuser edits settings directly
- **WHEN** a read-only superuser posts a tag-color, catalog-home, or other configuration mutation directly
- **THEN** the operation returns 403 without changing data even when the old guard checked only is_superuser

#### Scenario: Caller starts mutating work
- **WHEN** a read-only Principal invokes a plugin action that would enqueue a mutation job
- **THEN** no job or partial mutation is created

#### Scenario: Queued work outlives a privilege change
- **WHEN** a job initiated by a writable Principal starts its mutation after that Principal became read-only
- **THEN** it rechecks the initiating Principal and performs no mutation

### Requirement: Django admin cannot bypass the account restriction
Read-only staff and superusers SHALL be denied admin add/change/delete operations, inline writes, bulk actions, and custom mutation views across registered models, including users, AccountAccess, membership and permission grants. Admin view access SHALL follow existing permissions. A read-only administrator SHALL NOT clear its own flag, delete its AccountAccess row, or use admin authentication/break-glass as a write exemption.

#### Scenario: Read-only administrator removes its own restriction
- **WHEN** a read-only administrator submits a crafted UserAdmin inline update or deletion for its AccountAccess
- **THEN** the request is rejected and the restriction remains in force

#### Scenario: Read-only administrator invokes a bulk action
- **WHEN** a read-only administrator invokes a mutating admin action or custom mutation view
- **THEN** no records or jobs are changed, regardless of superuser status

### Requirement: Flag administration is authorized and audited
Normal flag changes SHALL require a non-read-only operator with explicit AccountAccess change permission and authority over the target User. Creation/change/deletion of the flag state SHALL record operator, target, old/new values, and timestamp atomically with the change. Creating an intended read-only account and its flag SHALL commit atomically before that account can authenticate. Deletion that restores the default false state SHALL receive equivalent authorization and audit; the normal inline UI SHALL use explicit false instead of deletion. An infrastructure-only recovery command SHALL require exact target and reason, offer safe dry-run output, and audit its action without exposing a callable web bypass.

#### Scenario: Operator creates a read-only account
- **WHEN** an authorized operator creates a User with read_only enabled
- **THEN** no successfully committed intermediate state allows that account to authenticate without the restriction

#### Scenario: Non-read-only operator removes a restriction
- **WHEN** an authorized non-read-only operator clears the flag
- **THEN** the change and its audit event commit together and ordinary authorization rules resume

#### Scenario: All writable administrators are unavailable
- **WHEN** an infrastructure operator executes the documented recovery command with exact target and reason
- **THEN** the selected restriction can be removed with an audit record, without permitting a read-only browser session to perform the same operation

### Requirement: Existing sessions observe current account restrictions
Core SHALL read current persisted AccountAccess state at each new request's authorization boundary and before user-triggered job mutations. After a flag change commits, subsequent such checks across all sessions/workers SHALL observe it without requiring reauthentication. Missing rows SHALL mean false; storage failures SHALL fail closed rather than be treated as missing rows. The flag SHALL NOT be authoritative session-cached state. Already committed or already authorized in-flight work is not required to be retroactively cancelled.

#### Scenario: Operator restricts an already logged-in user
- **WHEN** the operator sets read_only and an existing session next attempts a write
- **THEN** it receives 403 even if its frontend still shows writable controls

#### Scenario: Restriction is removed
- **WHEN** the flag is cleared and an existing session requests a write
- **THEN** normal permission evaluation resumes and the request is not automatically allowed

### Requirement: Authentication and service maintenance remain available
Read-only SHALL restrict user-initiated mutations, not all database writes or unsafe HTTP methods. Login/logout, session maintenance, audit, Core-controlled identity/profile/group provisioning, and explicitly supported credential recovery/change flows SHALL continue under their own security policies without permitting AccountAccess changes. Independently scheduled system ingestion SHALL retain its service authorization; a user request SHALL NOT impersonate that service or select a source parameter to bypass read-only.

#### Scenario: Read-only user authenticates and logs out
- **WHEN** the user completes a supported authentication or logout flow
- **THEN** required session and audit changes succeed while catalog mutations remain denied

#### Scenario: User attempts to impersonate ingestion
- **WHEN** a read-only caller supplies a system/ingestion source value to a mutation operation
- **THEN** it does not bypass the caller's restriction

### Requirement: Identity providers and membership changes preserve read-only
Authentication providers, external claims/groups, profile synchronization, identity linking, and automatic provisioning SHALL NOT assign, clear, overwrite, or delete AccountAccess. All identities linked to one Principal SHALL share its restriction. Manual/provider membership grants, Purge Grants, and admin break-glass SHALL NOT override it. When issuing an external account that must be read-only from first access, the documented procedure SHALL create the flagged Principal before linking and allowing its identity under preprovisioned policy; automatic unrestricted creation followed by later flagging SHALL not be presented as equivalent.

#### Scenario: Read-only user logs in through another provider
- **WHEN** an existing read-only Principal authenticates through a different linked identity or receives new external memberships
- **THEN** the flag remains set and write attempts are denied

#### Scenario: Membership storage is migrated
- **WHEN** legacy memberships become manual or provider-managed grants
- **THEN** read-only flags remain unchanged and no resulting grant authorizes a read-only Principal to write

#### Scenario: External read-only account is prepared
- **WHEN** an operator creates the flagged Principal, links its exact external identity and enables preprovisioned access
- **THEN** the first successful external login is already restricted without an unrestricted provisioning window

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
