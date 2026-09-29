## ADDED Requirements

### Requirement: Authentication providers use a versioned public extension point
Atlas SHALL expose a keyed `atlas.auth.providers.v1` extension point through `atlas_plugin_api`; a third-party authentication provider SHALL be implementable, registered, selected, and tested without importing `server.apps.*`, modifying Core source, or relying on undocumented allauth internals.

#### Scenario: Third-party provider uses only public contracts
- **WHEN** a plugin implements and registers a custom authentication provider
- **THEN** every Atlas import used by that plugin comes from the versioned `atlas_plugin_api` surface

#### Scenario: Duplicate provider id fails composition
- **WHEN** two selected plugins declare the same authentication provider id
- **THEN** composition fails before startup and identifies both owning plugins

#### Scenario: Missing selected provider fails composition
- **WHEN** `auth.providers` names a provider no selected plugin or Core component declares
- **THEN** composition fails before generating a runnable distribution

### Requirement: Providers declare one supported flow kind
Every authentication provider SHALL declare a flow kind whose Core contract is one of `credentials` or `redirect`; Core SHALL render and route the provider according to that declared kind rather than inferring behavior from provider ids or implementation packages.

#### Scenario: Credential provider uses the credential contract
- **WHEN** a selected provider declares `flow_kind=credentials`
- **THEN** Core presents the standard credential interaction and invokes the provider's credential-verification contract without requiring provider-owned frontend code

#### Scenario: Redirect provider uses the redirect contract
- **WHEN** a selected provider declares `flow_kind=redirect`
- **THEN** Core exposes start and callback behavior for that provider and invokes its redirect-flow contract

#### Scenario: Unsupported flow kind fails validation
- **WHEN** a provider descriptor declares a flow kind unknown to the installed Plugin API contract version
- **THEN** composition fails with a compatibility error rather than attempting a partial activation

### Requirement: Providers return normalized verified identities
A provider that successfully verifies credentials or a protocol response SHALL return a normalized verified identity containing its provider id, a stable source-scoped subject, the bound source id, profile attributes with verification provenance, and an explicit group snapshot status (`unsupported`, `complete`, or `unavailable`) with normalized values. It SHALL NOT establish the Django session, directly create or mutate Atlas authorization records, or assign Django staff/superuser status.

#### Scenario: Successful custom authentication returns an identity
- **WHEN** a custom provider verifies the remote identity successfully
- **THEN** it returns a normalized identity to Authentication Core and Core performs linking, provisioning, group reconciliation, and session establishment

#### Scenario: Provider attempts to grant administrative status
- **WHEN** a provider returns an attribute that represents administrator, staff, role, permission, or equivalent elevated status
- **THEN** Core treats it only as an external attribute and does not modify Django administrative flags or bypass the PolicyEvaluator

#### Scenario: Same provider subject is stable
- **WHEN** the same provider/source-scoped subject authenticates repeatedly
- **THEN** Core resolves every successful authentication to the same ExternalIdentityLink and Principal

### Requirement: Authentication Core owns common security behavior
Authentication Core SHALL own session creation and termination, CSRF policy, provider selection enforcement, return-URL validation, provisioning orchestration, and authorization handoff for every provider. A provider SHALL own only secure verification of its credential or redirect protocol and production of a normalized result.

#### Scenario: Provider cannot create a parallel session type
- **WHEN** a custom provider completes authentication
- **THEN** the resulting Atlas session uses the same Core-managed session and CSRF behavior as every built-in provider

#### Scenario: Unsafe return URL is rejected
- **WHEN** a provider start request supplies a return URL outside the configured Atlas origins
- **THEN** Core rejects or replaces it with a safe local destination before invoking the provider

#### Scenario: Unselected installed provider is invoked directly
- **WHEN** a provider package is installed but its id is absent from `auth.providers` and a caller requests its endpoint directly
- **THEN** Core returns a not-found or disabled-provider response without invoking provider code

### Requirement: Credential providers receive secrets only on the backend
The standard credential flow SHALL submit credential values only to the Atlas backend over the deployment's protected origin. Core and providers SHALL NOT persist, echo, include in structured logs, expose to frontend bootstrap state, or place in error details any submitted credential.

#### Scenario: LDAP password is verified
- **WHEN** a user submits a password to a selected LDAP credential provider
- **THEN** the password is passed to that provider only for the current verification attempt and is absent from persisted models, responses, and logs

#### Scenario: Credential provider raises an exception
- **WHEN** credential verification fails with an exception containing sensitive connection or credential context
- **THEN** the user receives a sanitized authentication failure and sensitive values are absent from application logs

### Requirement: Redirect providers isolate protocol state
Each redirect provider SHALL maintain protocol state namespaced by provider and source, bound to the initiating browser session and a Core-issued attempt generation, expiring after at most ten minutes and consumed atomically once. Providers SHALL validate every security property required by its protocol, including callback correlation and replay prevention. Core SHALL reject callbacks for unselected providers and SHALL NOT accept a normalized identity until provider verification succeeds.

#### Scenario: Callback state does not match
- **WHEN** a redirect callback carries missing, expired, replayed, or mismatched state
- **THEN** authentication fails without creating a Principal, ExternalIdentityLink, or session

#### Scenario: Callback targets another provider
- **WHEN** callback state created for one provider is presented to another provider's callback
- **THEN** Core and the provider reject it without cross-provider identity resolution

### Requirement: Providers expose safe health and failure information
An authentication provider MAY expose a health check, but health and authentication failures SHALL be isolated per provider and SHALL disclose no credentials, tokens, bind identities, client secrets, or unfiltered upstream response bodies.

#### Scenario: Default provider is unavailable and fallback exists
- **WHEN** the default provider is unhealthy or returns a recoverable authentication failure and another selected provider exists
- **THEN** the login experience offers the provider-choice fallback without disabling the healthy provider

#### Scenario: Health output is inspected
- **WHEN** an operator reads authentication provider health
- **THEN** the output identifies provider id, availability category, and safe remediation context without secret material

### Requirement: The SDK provides reusable contract tests
The Python Plugin API SHALL provide a provider contract-test kit that verifies descriptor/source identity, flow-kind behavior, attribute provenance, group snapshot completeness, failure sanitization, stable subjects, selection enforcement, and non-ownership of sessions and authorization. First-party providers and the custom credential example SHALL run the same contract suite.

#### Scenario: Provider passes the contract suite
- **WHEN** a plugin author runs the documented authentication provider contract tests
- **THEN** the suite exercises the mandatory behaviors for the provider's declared flow kind

#### Scenario: Provider returns an invalid identity
- **WHEN** a provider returns an empty subject, mismatched provider id, unsupported value, or a result attempting direct authorization assignments
- **THEN** the contract suite fails with the violated provider contract


### Requirement: Credential contract supports directory verification without directory coupling
The credential contract SHALL accept bounded non-empty username/password input, reject empty passwords before invocation, provide validated private configuration and a bounded operation deadline, and return either one fully verified identity or a typed invalid-credentials, unavailable, or invalid-result failure. Providers SHALL NOT return successful identities for anonymous bind, ambiguous user resolution, transport failure, or incomplete credential verification. User-facing invalid-credential responses SHALL not disclose account existence. The SDK SHALL not require LDAP-specific fields, frontend code, Core model access, or multi-step interaction to implement a search-and-bind LDAP flow.

#### Scenario: Empty password is submitted
- **WHEN** a caller submits an empty password to a credential provider
- **THEN** Core rejects it before provider invocation and creates no session

#### Scenario: LDAP provider is implemented against the contract
- **WHEN** a plugin searches a configured directory, verifies one user's password, and reads a stable directory id and groups
- **THEN** it can return source/subject, profile assurance, and complete or unavailable group state through public SDK types without writing Atlas models

#### Scenario: Verification is incomplete
- **WHEN** a credential provider times out, resolves multiple users, or cannot verify the password
- **THEN** it returns a failure and cannot fall back to a successful partial identity

### Requirement: OAuth and OIDC adapters meet a testable protocol baseline
Built-in OAuth/OIDC providers SHALL use Authorization Code flow with PKCE S256 and transaction-bound state; OIDC SHALL additionally use a transaction-bound nonce. The supported adapter/version SHALL pass these checks before it is advertised as supported. OIDC SHALL validate the signature using trusted issuer keys and allowed algorithms, exact issuer, audience and applicable authorized-party rules, expiration and applicable time claims with bounded clock skew, and nonce. UserInfo claims SHALL be used only when their sub exactly matches the validated ID-token sub. Algorithms or key locations supplied solely by an untrusted token SHALL not establish trust. Key rotation SHALL work through bounded refresh of the configured issuer's JWKS.

#### Scenario: Code or token is substituted
- **WHEN** a callback presents a code with the wrong PKCE binding, a mismatched nonce, an expired token, an invalid signature/algorithm, or the wrong issuer/audience
- **THEN** authentication fails before identity provisioning or session establishment

#### Scenario: UserInfo belongs to another subject
- **WHEN** UserInfo sub differs from the validated ID-token sub
- **THEN** authentication fails and no UserInfo profile or group data is applied

#### Scenario: Issuer rotates signing keys
- **WHEN** the trusted issuer publishes a new signing key and signs a valid token with it
- **THEN** the adapter can refresh its bounded JWKS cache and verify it without accepting arbitrary token-supplied key URLs

#### Scenario: Two callbacks consume the same state concurrently
- **WHEN** two requests attempt to complete one browser authentication transaction
- **THEN** at most one request can consume the state and reach provisioning

### Requirement: Provider context is a contract boundary rather than a sandbox
The SDK SHALL document that installed Python provider plugins are trusted server code with process privileges; narrow contexts, import checks, and contract tests SHALL NOT be described as isolation from a malicious plugin. Provider packages SHALL remain subject to the distribution's artifact provenance and compatibility checks. Contract tests SHALL verify cooperative conformance and negative result validation.

#### Scenario: Operator installs a third-party provider
- **WHEN** the operator follows the provider installation guide
- **THEN** it explains the server-code trust boundary and package review requirement without claiming the SDK can contain hostile code

### Requirement: Authentication abuse limits apply across routes and workers
Core SHALL apply bounded request/result sizes and distributed authentication rate limits covering credential failures, redirect starts/callback failures, signup, and recovery. Limits SHALL combine provider/account and deployment-level budgets with trusted client-address handling; aliases, different workers, or provider switching SHALL not reset aggregate budgets. Exhausted budgets SHALL return sanitized retryable failures without running prohibited verification or leaking account existence.

#### Scenario: Caller switches aliases or providers after throttling
- **WHEN** a client exhausts an aggregate authentication budget and retries through another selected provider or compatibility route on another worker
- **THEN** the applicable aggregate budget remains enforced

#### Scenario: Provider result exceeds configured limits
- **WHEN** a provider returns excessive attribute or group data
- **THEN** Core rejects the result as invalid rather than truncating it into a supposedly complete group snapshot
