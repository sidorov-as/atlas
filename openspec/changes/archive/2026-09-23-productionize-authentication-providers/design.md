## Context

Atlas currently authenticates browser users with `django-allauth` headless and protects catalog APIs with Django session cookies. The code contains a Core-internal `AuthenticationProvider` protocol, hard-coded `atlas.auth.local` and conditional `atlas.auth.oidc` registrations, an `ExternalIdentityLink` model, and post-login OIDC group mapping. The architectural intent is sound—authentication verifies identity, Authentication Core owns the session, and authorization remains centralized—but several implementation and product-contract gaps prevent safe deployment and third-party extension:

- the distribution manifest parses `auth.providers` and `auth.default`, but the composer, lock, generated backend/frontend configuration, and runtime do not consume them;
- `DEFAULT_AUTH_PROVIDER` is fixed to local and does not drive frontend or backend behavior;
- local login remains available regardless of selection, and allauth's headless signup operation is open by default even though Atlas documents no self-service signup;
- the headless redirect entry point is mounted while the allauth provider login/callback URL names required by OIDC are not, so the current browser OIDC flow cannot resolve its routes;
- OIDC configuration calls a value `issuer` while passing it to allauth as the directly fetched discovery document URL;
- provider discovery is derived from allauth rather than authoritative Atlas composition;
- OIDC group mapping requires an already-linked Actor, silently ignores users without one, only adds memberships, and cannot distinguish provider-managed membership from manual membership;
- the current provider protocol only resolves a Principal after authentication; it does not define how a plugin implements credential or redirect verification;
- the provider registry and identity models are Core internals, so a third-party LDAP/SAML/OAuth provider cannot be built against `atlas_plugin_api` alone;
- the login frontend understands only one hard-coded local form plus allauth social redirect buttons;
- there are guides for local and OIDC authentication, but no runnable authentication topology, selection guide, provisioning policy, exact callback reference, OAuth distinction, or custom-provider authoring contract.

The change crosses the composer, generated distribution inputs, Django settings and routing, Plugin API, Core identity models/services, frontend login, first-party providers, documentation, examples, and CI. Authentication is security-sensitive, and existing installations may implicitly depend on local login and the unintentionally open signup endpoint, so the implementation must be incremental, auditable, and rollback-aware.

### Current and target responsibility split

```text
CURRENT
=======

manifest auth fields (unused)
          |
          X
Core hard-codes local + optional OIDC settings
          |
allauth authenticates and creates session/user
          |
Core signal records ExternalIdentityLink and adds groups


TARGET
======

manifest + provider plugin descriptors
          |
          v
composer validates and generates selected auth runtime
          |
          v
provider verifies credentials/protocol response
          |
          v
VerifiedIdentity(provider_id, source_id, stable subject, assured profile, group snapshot)
          |
          v
Authentication Core
  - selection enforcement
  - link/provision/reconcile
  - session + CSRF + logout
          |
          v
PolicyEvaluator over ordinary Atlas state
```

## Goals / Non-Goals

**Goals:**

- Make manifest provider selection and default authoritative and reproducible.
- Disable local self-signup by default through server-side policy and reject direct use of unselected providers.
- Make local, OIDC, and provider-specific OAuth2 browser login work end to end with one session model and safe fallback UX.
- Publish a provider API that supports third-party credential and redirect flows without Core-internal imports.
- Keep Core—not plugins—responsible for sessions, provisioning, group synchronization, and authorization handoff.
- Define explicit Principal, Actor, profile, and Group reconciliation policies with auditable effects.
- Support provider-managed exact membership without removing manual or other-provider grants.
- Provide production-oriented guidance and runnable local development examples for local, Keycloak OIDC, Gitea OAuth2, and a minimal custom credential plugin, with LDAP implementability documented separately.
- Validate first-party and example providers with the same contract tests.
- Maintain a local break-glass option when an operator selects it, without forcing it on pure-SSO deployments.

**Non-Goals:**

- API bearer tokens, OAuth resource-server behavior, service accounts, or machine-to-machine authorization. Browser providers still establish Django sessions.
- A generic OAuth2 identity adapter accepting arbitrary JSON paths. OAuth provider identity and teams are provider-specific; this change ships Gitea as the first explicit OAuth2 adapter.
- A built-in SAML implementation. The redirect-provider contract is designed so a later plugin can implement SAML without changing Core.
- Multi-step/custom login UI, WebAuthn/passkeys, OTP enrollment, device authorization, mTLS, or trusted reverse-proxy/header authentication in provider-contract v1.
- Full upstream single logout for providers that do not support or configure it. Atlas always ends its own session and describes remote logout truthfully.
- Automatically creating Atlas Groups from arbitrary external group names by default.
- Granting staff, superuser, Purge Grant, or direct Atlas permissions from provider claims, scopes, LDAP attributes, roles, or groups.
- Shipping or certifying a production LDAP provider, directory lifecycle integration, nested-group discovery, or an OpenLDAP reference deployment. LDAP support must be implementable through v1, but the required custom example uses fixture credentials.
- Immediate upstream deprovisioning through SCIM or back-channel logout; v1 provides bounded freshness and explicit local revocation.
- Treating fixture credential providers or IdP example topologies as production infrastructure.

## Decisions

### 1. `auth.providers` becomes an ordered list of policy-bearing entries

The manifest evolves from a tuple of strings to entries that combine provider selection with Core-owned policy, while provider-specific connection/protocol configuration stays in the owning plugin's namespaced `plugins[].config` block.

```yaml
auth:
  publicOrigin: https://atlas.example
  sessionMaxAgeSeconds: 28800
  adminPasswordLogin: disabled
  adminPasswordPrincipalIds: []
  providers:
    - id: atlas.auth.oidc
      principalProvisioning: automatic
      actorProvisioning: automatic
      profileFields: [username, displayName, email]
      groupSync:
        mode: exact
        maxAgeSeconds: 28800
        unknownGroups: ignore
        mappings:
          engineering: engineering
    - id: atlas.auth.local
      signup: disabled
  default: atlas.auth.oidc

plugins:
  - id: atlas.auth.oidc
    version: 0.1.0
    backend: { package: atlas-plugin-auth-oidc, source: workspace }
    config:
      discoveryUrl: https://idp.example/.well-known/openid-configuration
      expectedIssuer: https://idp.example
      clientId: atlas
      clientSecret: { fromEnv: ATLAS_OIDC_CLIENT_SECRET }
      scopes: [openid, profile, email, groups]
      groupsClaim: groups
```

Core policy belongs under `auth` because its semantics must be consistent across implementations. Network endpoints, client registration, LDAP search configuration, or provider-specific API behavior remain typed plugin configuration.

The composer validates:

- at least one provider;
- unique provider ids;
- default belongs to the selected ids;
- each non-Core provider has a selected compatible owning plugin/artifact;
- provider descriptor flow metadata matches the runtime implementation;
- selected policy values are supported by the provider/contract version;
- required provider configuration and secret references validate.

The lock records provider order, default, flow metadata, Core policy, plugin version/hash, and unresolved secret references, never resolved values. Generated backend/frontend modules are derived from the lock.

**Alternative considered:** keep string ids and add unrelated global environment variables. Rejected because it preserves the current split brain and cannot express per-provider provisioning or synchronization safely.

### 2. Provider SDK v1 has separate credential and redirect protocols

The public Python contract is a keyed extension point identified as `atlas.auth.providers.v1`. Static metadata is importable before `django.setup()`; runtime provider instances register after setup.

Illustrative contract shape:

```python
class AuthFlowKind(StrEnum):
    CREDENTIALS = "credentials"
    REDIRECT = "redirect"


@dataclass(frozen=True, slots=True)
class AuthenticationProviderDescriptor:
    id: str
    display_name: str
    flow_kind: AuthFlowKind
    contract_version: str
    supports_remote_logout: bool = False


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    provider_id: str
    source_id: str
    subject: str
    profile: ExternalProfile
    attributes: Mapping[str, AssuredAttribute]
    groups: ExternalGroupSnapshot  # explicit unsupported | complete | unavailable


# Profile/attribute assurance distinguishes verified ownership, trusted
# authority-managed fields, and unverified self-asserted values.
# Only complete snapshots carry an authoritative tuple (which may be empty).


class CredentialAuthenticationProvider(Protocol):
    descriptor: AuthenticationProviderDescriptor

    def authenticate(
        self,
        context: CredentialFlowContext,
        credentials: CredentialInput,
    ) -> VerifiedIdentity | AuthenticationFailure: ...


class RedirectAuthenticationProvider(Protocol):
    descriptor: AuthenticationProviderDescriptor

    def begin(self, context: RedirectFlowContext) -> RedirectChallenge: ...
    def complete(
        self, context: RedirectCallbackContext
    ) -> VerifiedIdentity | AuthenticationFailure: ...
```

Contexts expose the minimum safe request/session collaboration required by the flow rather than raw Core registries or models. A result cannot carry Django `User`, Actor, Group, permissions, `is_staff`, or `is_superuser` assignments.

`atlas_plugin_api` exports:

- descriptors and flow enums;
- credential/redirect provider protocols;
- normalized profile and attribute assurance, source-bound verified identity, explicit group snapshots, challenge, and safe failure types;
- `register_authentication_provider(provider, owner=...)`;
- provider lookup needed by Core, not arbitrary mutation access;
- contract-test helpers.

**Alternative considered:** declare Django authentication backends or allauth adapters as the public extension API. Rejected because that leaks implementation, lets providers bypass Core provisioning/session policy, makes frontend behavior implicit, and couples compatibility to third-party framework internals.

### 3. Static and runtime provider contributions are deliberately split

Provider plugins need settings-time information before the existing runtime entry-point phase. `PluginDescriptor` gains an implementation-free authentication contribution containing provider descriptors, config schema references, Django apps, and (only when unavoidable) namespaced URL modules. Runtime `register_runtime()` supplies provider instances after Django is ready.

The composer uses static descriptors to generate `INSTALLED_APPS`, selected provider metadata, and provider-specific static setup. Runtime loading verifies that every selected descriptor has exactly one matching registered instance and no unselected implementation becomes active.

Local authentication remains a Core-owned built-in provider because it is the recovery/bootstrap mechanism and requires no separate artifact. OIDC is extracted from `server.apps.catalog` into a first-party `atlas.auth.oidc` provider plugin using the public contract. Gitea is a separate first-party `atlas.auth.gitea` plugin. The custom credential example is a separately packaged development-only fixture plugin and is not part of the default distribution. The SDK guide independently maps LDAP search-and-bind to the same contract.

**Alternative considered:** leave OIDC in Core and only publish the protocol for future providers. Rejected because first-party use of the public surface is the strongest compatibility test and prevents the SDK becoming aspirational.

### 4. Core owns stable authentication gateway behavior

Core exposes a stable Atlas-owned browser authentication API rather than asking the frontend to construct allauth/provider-specific routes:

```text
GET    /auth/browser/v1/config
GET    /auth/browser/v1/session
DELETE /auth/browser/v1/session
POST   /auth/browser/v1/providers/{provider_id}/credentials
POST   /auth/browser/v1/providers/{provider_id}/start
GET    /auth/browser/v1/providers/{provider_id}/callback
POST   /auth/browser/v1/signup                 # only when explicitly enabled
GET    /login                                  # application login route
GET    /login?choose-provider=1                # no auto redirect
```

Credential and redirect operations validate selection and flow kind before provider invocation. Callback correlation is namespaced by provider/source, bound to the initiating browser session and Core attempt generation, valid for at most ten minutes, and atomically consumed once. Core validates return URLs against the configured public origin/allowlist, rejecting scheme-relative and ambiguously encoded destinations. A provider library may require internal callback helpers, but those are mounted beneath its selected namespaced path and are not the public frontend contract.

Existing `/_allauth/browser/v1/*` operations remain temporarily as compatibility aliases during migration. They pass through the same selection/signup policy; no alias may bypass it. Once the frontend, examples, and documented integrations use the Atlas gateway, removal of the compatibility surface requires a separate deprecation decision.

For the immediate allauth-backed implementation, the missing allauth provider URL patterns are mounted so reverse resolution and callback work. The Atlas gateway remains the long-term stable boundary.

**Alternative considered:** expose allauth headless and provider URLs as the permanent Atlas API. Rejected because a third-party LDAP provider and future non-allauth redirect provider would otherwise have different lifecycle, errors, and selection enforcement.

### 5. Local signup is denied by policy, not hidden for security

Atlas supplies an `AccountAdapter` whose `is_open_for_signup()` reads generated authoritative auth policy. Default is false. Direct posts to allauth compatibility routes and Atlas routes use the same adapter/policy. UI and public config hide signup when closed, but tests assert server rejection.

Local login is separately gated by provider selection. Disabling local signup does not disable administrator-created local accounts. Disabling `atlas.auth.local` blocks catalog local login. Admin password login is separately disabled by default; an explicit `adminPasswordLogin: break-glass` requires a non-empty allowlist of pre-existing active staff Principal ids. Such a login creates the same bounded Core session and therefore can also access catalog APIs under normal authorization; the guide must describe this exception to SSO-only operation. An existing valid SSO session may access admin when the Principal has staff permission. The official local distribution documents bootstrap and explicit allowlisting rather than silently enabling admin password access.

Social/external auto-provisioning is not called “signup” in configuration and is controlled by `principalProvisioning`; closing local signup must not inadvertently prevent selected external automatic provisioning.

**Alternative considered:** remove only the signup URL. Rejected because route changes are brittle and do not prove that another allauth code path cannot create a local account.

### 6. Default-provider UX always preserves explicit choice

Frontend bootstrap is Atlas-owned and contains only safe presentation state:

```json
{
  "providers": [
    {
      "id": "atlas.auth.oidc",
      "displayName": "Company SSO",
      "flowKind": "redirect",
      "isDefault": true
    },
    {
      "id": "atlas.auth.local",
      "displayName": "Username and password",
      "flowKind": "credentials",
      "credentialFields": ["username", "password"],
      "signupOpen": false
    }
  ],
  "providerChoiceUrl": "/login?choose-provider=1"
}
```

Behavior:

| Selection | `/login` behavior |
| --- | --- |
| local only | render credentials |
| one redirect provider | begin redirect |
| multiple, local default | render local primary plus provider buttons |
| multiple, redirect default | begin default redirect once; explicit choice suppresses redirect |
| redirect error with fallback | return to provider choice with sanitized error |

Provider state carries the safe return path. An error marker/cookie/query flag prevents immediate redirect loops. UI never renders an installed-but-unselected provider.

**Alternative considered:** always show all buttons and treat “default” as ordering only. Rejected because the existing spec says visitors are directed to the default first and pure SSO deployments expect direct entry.

### 7. OIDC uses discovery URL and validates issuer explicitly

OIDC plugin configuration separates:

- `discovery_url`: URL returning the OpenID Provider Configuration document;
- `expected_issuer`: explicit expected `issuer`, bound to the identity source; never learned from an unverified login;
- client id and secret reference;
- scopes;
- group claim name;
- provider display name and optional remote logout configuration.

The plugin uses an established OIDC implementation (initially allauth's OpenID Connect provider behind the public Atlas contract) for authorization redirect, state/nonce, token exchange, signature validation, issuer/audience validation, and userinfo. Core uses `(provider_id, source_id, subject)` as the stable external identity key, with the validated OIDC issuer as source id. A source binding cannot be silently repointed while retaining existing links. A new issuer under the same provider id is a new namespace; transferring an identity requires an audited operator action. Gitea uses a configured instance namespace bound to its canonical origin, and future LDAP providers use an immutable directory namespace plus stable UUID. Concurrent independent provider instances remain outside v1; this does not relax source identity checks.

Diagnostics can report discovery reachability, issuer mismatch category, callback URL, selected scopes, and provider id, never tokens or secrets. The exact callback is derived by URL reversal and surfaced in safe operator output and docs.

**Alternative considered:** continue calling `server_url` an issuer. Rejected because the current library fetches it directly as discovery JSON and the ambiguity produces broken client registrations.

### 8. OAuth2 support is provider-specific; Gitea is the first implementation

OAuth 2.0 defines delegated authorization, not a stable identity/profile/group schema. Atlas therefore does not ship a generic endpoint/JSON-path adapter in this change. `atlas.auth.gitea` wraps an established Gitea OAuth2/allauth implementation internally, normalizes Gitea's stable user id and supported profile attributes, and declares whether team mapping is supported. If the adapter cannot reliably obtain teams under documented scopes, group synchronization remains `none` and the example demonstrates operator-managed Atlas memberships.

GitHub, GitLab, Microsoft, and other adapters can follow the same provider contract later. Documentation lists only implemented adapters and does not imply interoperability from the word OAuth.

**Alternative considered:** a configurable generic OAuth adapter with authorization/token/userinfo URLs and JSON paths. Rejected for v1 because stable identity, error behavior, pagination, teams, enterprise hosts, and token authentication differ enough to make such configuration an unsafe mini-language.

### 9. Provisioning is a Core pipeline with explicit transaction boundaries

After provider verification, Core performs:

```text
validate normalized result
  -> resolve/link ExternalIdentity
  -> apply Principal provisioning policy
  -> apply allowed profile updates
  -> resolve/create/link Actor
  -> normalize/map external groups
  -> reconcile membership grants
  -> write audit events
  -> establish session
```

Policies:

- Principal: `preprovisioned`, `automatic`, `restricted`;
- Actor: `manual`, `automatic`;
- profile: explicit allowlist of provider-managed fields;
- groups: `none`, `additive`, `exact`;
- unknown groups: `ignore`; explicit mappings only, with no implicit exact-name mapping in v1;
- reconciliation failure: fail closed before session, with no v1 fail-open switch; missing/unavailable/partial group data is not an empty complete set;
- restricted eligibility: trusted, provenance-bearing attributes evaluated on every login, with verified ownership required for an email-domain restriction and exact normalized-domain comparison; loss of eligibility revokes that link's sessions/grants;
- profile updates: a fixed non-security field set, never active status, read_only, staff/superuser, passwords, identity links, or recovery destinations without independent verification.

The database portion runs atomically. Network verification happens before the transaction, under a Core-issued attempt generation and captured Principal revocation generation when known. Database uniqueness and per-Principal/link serialization prevent duplicate identity/Actor creation and an older snapshot overwriting a newer accepted attempt. Session creation happens only after commit and rechecking Principal/link/provider validity. Link collisions fail without reassignment or automatic email/username matching. Actor automatic mode also handles existing Principals missing an Actor. Success audit is committed with mutations; sanitized failure events are emitted outside a rolled-back transaction.

The default official distribution preserves behavior conservatively: local users remain operator-created; external Principal auto-provisioning can be enabled by the example/distribution; Actor provisioning and exact sync require explicit selection during migration rather than silently changing existing users.

**Alternative considered:** let each provider create Users/Actors and write memberships. Rejected because it duplicates security logic, prevents consistent audit/reconciliation, and allows provider attributes to become authorization decisions.

### 10. Membership origin becomes first-class

Exact reconciliation cannot be implemented safely with the current bare Group-members M2M because Atlas cannot tell whether a membership is manual, OIDC-managed, LDAP-managed, or supported by multiple sources. Introduce an explicit membership-grant model representing one reason an Actor belongs to a Group:

```text
GroupMembershipGrant
  actor
  group
  source_kind: manual | provider
  identity_link: null for manual | exact provider/source/subject link
  legacy_unclassified: bool
  expires_at: required for exact-mode provider grants
  external_key: optional normalized external group key
  created_at / last_confirmed_at

effective membership(actor, group) := at least one applicable, unexpired grant exists
```

Existing memberships migrate to `manual` grants marked legacy-unclassified. A dry-run report and audited operator command classify them or transfer reviewed grants to an exact external identity link without leaving a manual duplicate. Enabling exact on a legacy deployment requires explicit classification or acknowledgement of retained legacy grants; no historical provider ownership is guessed from claims. Provider additive/exact sync owns grants per identity link, so separately linked identities do not erase each other's grants. Exact sync accepts only complete snapshots, removes stale grants owned by that link, and sets a finite expiry (eight hours by default) on confirmed grants. A complete empty snapshot removes that link's grants; unavailable groups fail login and do not renew expiry. Effective membership remains while any independent applicable grant remains. Group permission checks move to the effective membership service/query rather than assuming a single undifferentiated M2M row.

Manual UI/admin/ingestion membership operations create/remove manual grants. Removing a manual grant cannot remove an active external grant; the operator UI/documentation reports remaining sources. Audit events accompany provider and manual changes.

**Alternative considered:** maintain a side ledger only for provider-added memberships while retaining an untyped M2M. Rejected because a later manual “add” of an already externally present pair cannot be distinguished, so exact sync could still remove intended manual access.

### 11. Provider failures are isolated and sanitized

Provider invocation catches declared safe failures separately from unexpected exceptions. User-facing errors expose a stable category and correlation id, not upstream bodies, stack traces, directory details, tokens, or secrets. Logs apply central redaction and include provider id, stage, safe category, and correlation id.

An unhealthy default provider does not deactivate alternatives. Provider health is advisory and safe; it may test static configuration/discovery/connectivity with bounded timeouts but never authenticates a user or exposes secret values. Composition errors remain fatal because the declared distribution is invalid; runtime provider outage is isolated.

Rate limiting applies per authentication operation/provider in addition to existing Axes protection for local credentials. LDAP credential failures must not reveal whether a username exists. Redirect callback failures must reject missing/mismatched/replayed state before provisioning.

**Alternative considered:** return raw provider errors to simplify troubleshooting. Rejected because auth responses routinely include tokens, usernames, endpoints, and directory details.

### 12. Logout is local-first and remote capability-aware

Core invalidates the Atlas session for every logout request. A provider may declare a remote logout hook and safe redirect metadata. Remote failure does not resurrect the local session. UI and documentation say “signed out of Atlas” unless remote logout completed; they do not promise IdP-wide logout by default.

The session records provider/source, identity link where applicable, authentication time, and Principal revocation generation. Core uses these only to validate session lifetime/revocation and support logout/diagnostics, never to grant permissions. See Decision 15 for validity checks.

### 13. Examples are complete, isolated, and intentionally disposable

Create:

```text
examples/authentication/
  README.md
  local/
    compose.yaml
    .env.example
    README.md
  oidc-keycloak/
    compose.yaml
    .env.example
    README.md
    keycloak/realm.json
  oauth2-gitea/
    compose.yaml
    .env.example
    README.md
    gitea/app.ini
    gitea/bootstrap.sh
  custom-credentials/
    compose.yaml
    .env.example
    README.md
    plugin/...  # deterministic development-only credential fixtures
```

Each is independently runnable from its directory, uses project names/volumes that do not collide, contains health checks/start ordering, pins example dependency versions, and documents resource cost and cleanup. Fixed development credentials are clearly marked disposable; no example default is copied into production docs.

The Keycloak realm imports client, callback, users, and groups. The Gitea bootstrap creates the OAuth application repeatably through supported CLI/API behavior without checking generated client secrets into source when avoidable. The custom plugin uses deterministic disposable credentials and identity/group fixtures under explicit development-only configuration, requires only Atlas/PostgreSQL, and runs the public provider contract suite. The LDAP authoring section maps directory config, search-and-bind, TLS verification, filter/DN escaping, rejection of empty/anonymous/ambiguous binds, stable directory UUIDs, and complete group retrieval to public SDK inputs/results. No LDAP client or OpenLDAP deployment is required for release. Protocol implementations remain responsible for these checks; the generic contract must represent their success and failure unambiguously.

CI tiers:

- fast: YAML/JSON/LDIF parsing, `docker compose config`, docs links, schema validation, secret scanning, provider contract tests;
- integration: start each topology, health checks, login/callback or credential smoke, provisioning assertions, allowed/denied action, logout;
- browser: representative local and redirect provider-choice/fallback flow.

**Alternative considered:** one large Compose file with profiles. Rejected because readers cannot see the minimum topology for one authentication method and profile interactions make examples harder to copy and validate independently.

### 14. Documentation is task-, concept-, and reference-layered

Add an authentication overview/selection matrix, then focused guides for local, OIDC, provider-specific OAuth2, provisioning, group synchronization, custom provider development and LDAP implementation mapping, security, and troubleshooting. Concepts define External Identity, Principal, Actor, Group/Team label, membership grant, administrative flags, Purge Grant, and session. Reference documents exact manifest/provider fields, public SDK types, routes, error categories, callback construction, and lifecycle.

Every guide links to a runnable example and includes prerequisites, outcome, exact steps, verification of allowed and denied access, logout semantics, failure modes, and production caveats. Docs explicitly state that browser OIDC/OAuth does not make catalog APIs accept bearer tokens.

Source validation consumes actual schemas/routes/provider ids where practical; duplicated commands/config snippets are extracted or checked so docs cannot silently drift.

### 15. Session validity and grant freshness have finite bounds

Core session maximum age defaults to eight hours, configurable to another finite positive duration. Activity does not slide the absolute deadline. Session creation and every authenticated request, including plugin APIs and admin, check active/blocked status, revocation generation, link revocation, provider/source selection, absolute expiry, and continuing admin break-glass allowlist authorization where applicable. Operator block/revoke-all increments the Principal generation, invalidating outstanding sessions and preventing older in-flight attempts from establishing a usable session. Deployment changes shorten applicable lifetimes immediately and removal of a provider/source invalidates its sessions and grants; rollback/reselection cannot resurrect explicitly revoked sessions or grants.

Exact-mode grants have a separate finite freshness interval, also eight hours by default. Effective-membership queries exclude expired grants immediately without a cleanup-job dependency. API activity, other-provider logins, or failed verification cannot extend expiry. Additive mode intentionally retains membership until explicit removal or source/link revocation and is documented accordingly. IdP removal without notification is detected at the next verification, bounded for existing sessions/grants by these deadlines. An explicitly independent manual or other-identity grant remains effective. Instant upstream deprovisioning is not promised.

**Alternative considered:** leave Django session defaults and reconcile only at the next voluntary login. Rejected because another provider or a long-running browser session could otherwise keep stale external access indefinitely.

### 16. Operator identity and migration operations use exact identifiers

Provide management commands with safe dry-run output for identity inspection, preprovisioned linking, revocation/restoration, source migration, legacy grant classification, and Principal session revocation. Targets use exact provider/source/subject/Principal ids, never fuzzy profile matching. Administrative targets require an explicit privileged-target option. Revocation retains a marker that blocks automatic reprovisioning and invalidates that link's sessions/grants. Source backfill for existing OIDC links requires operator confirmation of the historical issuer; absent reliable source evidence, external login remains blocked until reviewed, with infrastructure recovery available.

**Alternative considered:** silently attach matching email/username or backfill source from the first new login. Rejected because either can transfer access to the wrong identity.

### 17. Security defaults are explicit rather than inherited from libraries

- OAuth/OIDC use Authorization Code plus PKCE S256; OIDC adds nonce, signature/algorithm, issuer/audience/authorized-party, and token time checks. UserInfo sub must match the ID token. Trusted JWKS rotation is tested with bounded refresh. The Gitea adapter spike must prove the baseline or report support blocked rather than silently weaken it.
- Production sessions use Secure/HttpOnly cookies, explicit SameSite=Lax for v1 GET callbacks, CSRF on login/start/signup/logout and account mutations, session-id rotation on login, and non-cacheable auth responses. SPA CSRF cookies remain readable but Secure. Configured public origin and trusted proxies govern URLs; untrusted Host/forwarded headers cannot select callbacks.
- Outbound identity requests enforce TLS certificate/hostname validation, bounded connection/read/overall deadlines and response sizes, and explicit allowed destinations. Validate discovery endpoints, redirects and resolved addresses; reject cloud metadata access, arbitrary user-selected URLs, plaintext downgrades, and cross-origin credential forwarding. Private IdPs require explicit trusted destinations. Development HTTP fixtures require an explicit development-only exception.
- Local passwords default to a fifteen-character minimum, common-password and user-similarity checks, acceptance of at least sixty-four characters, and no truncation. Bootstrap/change/signup/reset share validation. Recovery defaults to operator-managed; public reset is gated on explicit verified-address/mail/token/throttling configuration. External profile email cannot silently become a recovery address. Resets revoke sessions.
- Tokens are discarded after verification by default, including disabling library token persistence. Optional remote logout token retention requires bounded protected server-side storage and deletion; no client-visible session/token storage. Query/body redaction covers callback access logs, proxies, traces and CI artifacts, with safe allowlisted error fields.
- Rate limits cover credential attempts, redirect starts/callback failures, signup and recovery across processes and compatibility routes, using trusted client-address handling, account/provider and deployment-wide budgets; provider switching cannot reset the whole budget. Input and normalized claim/group sizes are bounded.
- Installed Python plugins are trusted server code, not sandboxed by the SDK. Contract tests and import rules enforce cooperative API conformance rather than containing malicious plugins.

**Alternative considered:** rely on allauth/Django/provider defaults. Rejected because gateway extraction, configuration, custom providers, and package upgrades can change which protections actually run.

### 18. Integrate the existing read-only account restriction

`add-readonly-role` is an implementation prerequisite and owns the read-only model, permission-effect classification, guarded evaluator, admin mutation checks, flag audit/recovery, and live access-state semantics. It was implemented and archived as `2026-09-20-add-readonly-role`; this change is refreshed against the resulting code and main-spec contracts. Do not copy its implementation into providers or replace the Core guard with an authentication-specific permission check.

All supported login paths, gateway/compatibility routes and admin break-glass establish identities/sessions only. Downstream mutation requests continue through the mandatory Core restriction before any selected evaluator or privilege shortcut. Break-glass is permission to authenticate, not permission to clear one's own flag. Read-only users may complete login/logout and Core-owned provisioning under the existing service-operation exceptions, but those operations cannot mutate AccountAccess.

Provider results, profile synchronization, new links to an existing Principal, source migration and membership migrations preserve AccountAccess exactly. This prohibition includes writing false, deleting the row, recreating it with defaults, or assigning read-only from external claims. Ordinary automatic provisioning continues to use the default account state; it is not a way to issue a guaranteed read-only account. Membership remains independent: manual/provider grants and Purge Grants remain stored normally but cannot override the account restriction.

Issue an external account that must be read-only from first access in this order: create the Principal and read-only state atomically through the existing operator workflow, create the exact provider/source/subject link using the new identity administration command, then permit the identity through `preprovisioned` policy. Do not allow automatic login before the flag/link setup completes. The guide includes a first-login read success/write rejection check and explains that auto-create followed by later flagging leaves a writable window. No provider claim-to-role mapping is added.

The new session/frontend flow continues fetching current `isReadOnly` from `/api/me/` after every successful login and preserves focus/visibility, mutation-route and write-denial refresh behavior from the prerequisite. It never freezes the flag in a signed/session authentication claim. Toggling the flag affects the next authorization check in existing external sessions; clearing it restores ordinary permission evaluation rather than unconditional access.

Integration-sensitive files include authorization.py, api/permissions.py, admin.py, auth.ts, SessionContext and model migration dependencies. Preserve the shared read-only guard while replacing membership queries with effective-grant queries, and extend the existing custom UserAdmin rather than replacing its inline/permission/audit behavior. Reconcile migration dependencies without recreating or dropping AccountAccess. Rollback must preserve both authentication protections and the read-only restrictions already assigned.

Release acceptance combines the prerequisite's regression suite with tests for repeated login, a different linked provider, profile/claim updates, new manual/provider grants, source/link operations, membership migration, read-only superuser/Purge Grant, explicit admin break-glass, and a live external session after flag on/off. The result is unchanged read behavior under normal permissions and denial of user writes before any effects when read-only is set.

**Alternative considered:** add a read-only setting to each provider or reconstruct it from group claims. Rejected because the restriction belongs to the Principal and must survive every provider and membership transition.

## Focused design resolutions

These decisions close the implementation-blocking questions from task group 1.

### Gateway prefix

The canonical public browser-authentication prefix is `/auth/browser/v1/`. It is an Atlas-owned product API and therefore does not use a private-looking underscore prefix. Existing `/_allauth/browser/v1/*` routes remain compatibility aliases only and must pass through the same selection, signup, CSRF, rate-limit, and session policy. Provider-library callback helpers may remain under selected, namespaced internal routes, but frontend code, examples, and new documentation use only `/auth/browser/v1/`.

### Gitea adapter baseline

The v1 adapter baseline is the repository-locked `django-allauth==65.19.1` Gitea provider against pinned Gitea `1.27.3`. The source-level spike records these constraints:

- the stable subject is the decimal string form of Gitea's immutable numeric `User.id`; `login`, email, and display name are mutable profile fields and never identity keys;
- the adapter fetches `GET {canonicalOrigin}/api/v1/user` and sends the OAuth access token in `Authorization: token <token>`; the instance source id is the normalized configured HTTPS origin, without a trailing slash;
- Gitea now requires a scope. Atlas requests exactly `read:user` for v1 authentication. The allauth provider's empty default scope is not accepted as a security default, so composition must inject and test this explicit scope;
- authorization and token endpoints are `/login/oauth/authorize` and `/login/oauth/access_token`; the allauth callback name remains `gitea_callback` at `/accounts/gitea/login/callback/` behind the transitional adapter, while the Atlas public callback is `/auth/browser/v1/providers/atlas.auth.gitea/callback` and bridges to that adapter internally;
- allauth supports opt-in OAuth PKCE and generates S256 challenges, while Gitea 1.27.3 supports Authorization Code with PKCE. Atlas must force `oauth_pkce_enabled=true`; unsupported or downgraded combinations fail composition or login rather than falling back;
- Gitea exposes paginated `/api/v1/user/teams`, which would additionally require `read:organization`, but the installed adapter fetches only `/api/v1/user` and provides no complete-snapshot or pagination contract. Consequently v1 declares Gitea group synchronization `none`; scopes never become Atlas grants. A later adapter revision may add teams only with complete pagination, stable organization/team keys, and contract coverage.

The executable provider/container proof remains required by tasks 11.2, 11.7, and 15; this focused spike fixes the contract and blocks silent weakening before that implementation work.

### Provider health and diagnostics

Provider health uses a dedicated `GET /healthz/auth/providers/` response rather than extending `/healthz/plugins/`. Plugin health reports selected artifact lifecycle and sticky unhandled plugin failures; authentication diagnostics report selected provider registration, static configuration, and bounded upstream reachability. The response evaluates providers independently, returns an overall 503 when any selected provider is unavailable without suppressing healthy alternatives, and exposes only allowlisted fields: provider id, selected/default state, flow kind, safe status/category, canonical callback URL, and correlation id. It never includes exception text, discovery/userinfo bodies, credentials, tokens, client secrets, subjects, claims, or resolved secret values. Checks use provider-specific bounded timeouts and cannot authenticate a user.

### Standard Catalog Actor provisioning boundary

`atlas.standard-catalog` owns Actor persistence and publishes an implementation-free collaboration service through `atlas_plugin_api`; Authentication Core never imports `atlas_plugin_standard_catalog.models`. The public surface consists of frozen DTOs plus an `ActorProvisioningService` protocol, `bind_actor_provisioning_service(service, owner=...)`, and Core read access through `get_actor_provisioning_service()`:

- `resolve_for_principal(principal_id)` returns an optional public Actor reference;
- `ensure_for_principal(request)` accepts the exact Principal id, normalized proposed name/display name/email, provenance, and correlation id, and returns an Actor reference plus created/linked status;
- `link_existing(request)` requires an exact Actor reference and Principal id for audited operator/preprovisioned workflows.

The Standard Catalog runtime binds the sole implementation after Django setup and performs its own Entity Service transaction, uniqueness, naming, and kind validation. Core chooses policy and supplies verified, allowlisted values; the service cannot establish sessions, edit AccountAccess, assign groups/permissions, or inspect provider tokens. Missing, disabled, or duplicate service ownership is a composition/runtime provisioning failure, never a fallback to direct ORM access.

### Membership administration with multiple grants

Admin and API views present one effective Actor-to-Group membership with an expanded list of contributing grants. Each grant exposes its immutable id, source kind (`manual` or `provider`), provider/source/subject display identifiers when applicable, legacy-classification state, last-confirmed time, expiry, and current applicability; raw claims and secrets are excluded.

The ordinary members editor creates and deletes only manual grants. Removing a manual grant deletes exactly that grant and reports whether another applicable grant still keeps the membership effective. Provider-managed grants are read-only in the ordinary members editor: their action links to the exact identity-link/source revocation or mapping workflow, which removes only grants owned by that link/source and records audit/revocation state so a later login cannot silently resurrect revoked access. Bulk replacement of a Group's `members` means replacement of manual grants only. API mutation addresses grants by immutable grant id and uses optimistic concurrency; it never deletes all grants for an Actor/Group pair implicitly. Every response returns both `effective` and remaining grant summaries so callers cannot report removal success as loss of access when another source remains.

### Source binding, revocation, expiry, and ordering

External identity storage uses the unique key `(provider_id, source_id, subject)`. Source ids are immutable canonical strings: exact validated issuer identifiers for OIDC, normalized HTTPS origins without trailing slash for Gitea, and an operator-declared immutable `urn:atlas:directory:<deployment-namespace>` for directory plugins. A selected provider configuration stores a source-binding record containing the provider id, source id, non-secret configuration fingerprint, lock digest, generation, and activation/revocation timestamps. Changing an authority creates a new source binding; it never rewrites links in place.

Backfill and source transfer use a versioned JSON document, accepted by an audited dry-run-first management command:

```json
{
  "version": 1,
  "providerId": "atlas.auth.oidc",
  "fromSourceId": null,
  "toSourceId": "https://idp.example",
  "links": [{"principalId": 42, "subject": "248289761001"}]
}
```

Every row is addressed by exact Principal/provider/source/subject identifiers. The command verifies collisions and expected counts, requires explicit confirmation for privileged Principals, records the input digest and operator, and never infers identity from email or username. Reversal is another audited transfer using the recorded prior source; revocation markers and generations are preserved.

Principal, identity-link, source-binding, and selected-auth-policy revocation generations are persisted in the database. Sessions and authentication attempts capture the applicable generations and source/config digest. Every authenticated request, including admin and plugin APIs, compares current persisted state; lookup failure fails closed and process-local caches are never authoritative. Revocation or deselection locks the row and atomically increments its generation, invalidating all workers without broadcast correctness assumptions.

Effective membership is defined by an indexed database predicate, not a cleanup job: the grant is not revoked, its link/source is active, and either it is manual/additive with no expiry or `expires_at > database_now()` for exact mode. Exact grants always have a finite expiry. Queries use the database clock and indexes beginning with `(actor_id, group_id)` and with `expires_at`/link ownership for authorization and expiry scans; cleanup may delete historical rows but cannot determine access.

Core creates a persisted authentication attempt and obtains a database-sequence generation before invoking provider code. Redirect state carries that attempt id/generation; credential flows use the same record. Provisioning locks the resolved link and Principal, verifies captured revocation/config generations, and applies profile/grant snapshots only when the attempt generation is greater than the link's `last_applied_generation`. It updates `last_applied_generation` in the same transaction as provisioning and audit. Thus an older, slower response cannot overwrite a newer accepted snapshot, and any revoke-all/source change after attempt creation prevents session establishment. Session creation occurs after commit and repeats the validity checks.

### Read-only prerequisite refresh

The archived `2026-09-20-add-readonly-role` change has every task complete and its deltas are present in the main `catalog-auth` and `policy-evaluator-extension` specs. Authentication work retains the current `AccountAccess` side-car, `is_account_read_only` current-state predicate, `CoreGuardedEvaluator`, custom `UserAdmin` inline/audit behavior, and `/api/me/` plus frontend refresh contract. New migrations depend forward from `0025_accountaccess`; provider/link/profile/membership operations never set, clear, delete, or recreate AccountAccess. The prerequisite regression suite is the baseline for every later authentication stage, with the combined cases listed in Decision 18.

## Risks / Trade-offs

- **[Authentication scope is large and cross-cutting]** → Implement in vertical stages: authoritative selection and hardening first, provider gateway/SDK second, provisioning origins third, built-in migrations fourth, examples/docs last. Keep local session regression tests green at every stage.
- **[Closing signup breaks an accidental behavior]** → Treat as an intentional security breaking change, add release/migration documentation, provide explicit opt-in, and test both compatibility route and new gateway.
- **[Making manifest auth authoritative breaks manifests with empty defaults]** → Add precise composer diagnostics and update the official manifest in the same stage; do not silently infer local after the migration boundary.
- **[Exact reconciliation can remove access unexpectedly]** → Require explicit `exact`, introduce source-aware grants first, default unknown groups to ignore, audit every removal, and preserve manual/other-provider grants.
- **[Membership model migration affects every authorization check]** → Migrate to marked legacy manual grants, classify or explicitly acknowledge retained grants before exact, verify counts, update shared accessors, and exercise rollback.
- **[Third-party provider code handles credentials/tokens]** → Keep credentials backend-only, publish narrow contexts/results, centralize redaction, require contract tests, document secure dependency review, and isolate failures/timeouts.
- **[Generic plugin routes could expand attack surface]** → Prefer Core-owned gateway endpoints; permit provider URL modules only when required and namespace/selection-gate them.
- **[Auto redirect can create loops]** → Provide a permanent explicit-choice URL and one-attempt/error suppression state.
- **[OIDC libraries and providers disagree on discovery/logout details]** → Separate discovery URL from expected issuer, validate metadata, expose exact callback safely, and make remote logout capability explicit.
- **[OAuth example may be mistaken for generic OAuth support]** → Name it Gitea everywhere, document provider-specific identity behavior, and avoid `atlas.auth.oauth2` as an implementation id.
- **[Example IdPs are resource-heavy and slow in CI]** → Split fast validation and image-backed integration jobs while requiring the latter before release.
- **[Custom example mistaken for production auth]** → Gate fixture credentials on development configuration, document LDAP implementation obligations separately, and do not ship a production LDAP claim.
- **[Admin password recovery bypasses SSO]** → Default it off, require explicit account allowlisting, and test/document that allowed admin sessions can access catalog APIs.
- **[Compatibility aliases prolong allauth coupling]** → Mark them compatibility-only, route them through the same policy, and track eventual removal separately.

## Migration Plan

**Prerequisite complete:** `add-readonly-role` is archived, this change is refreshed against its main specs and implementation, and its regression suite is the authentication baseline.

The stages below describe implementation order, not independently releasable security states. New authentication routes remain unpublished or disabled until source binding, provisioning, session validity, and mandatory negative tests are wired end to end.

1. **Contract and composer groundwork**
   - Add versioned provider descriptor/result/protocol types and contract tests to `atlas_plugin_api`.
   - Extend manifest schema, composition validation, lock, and generated backend/frontend auth modules.
   - Update the official distribution to explicitly select local auth, disabled signup, and conservative provisioning.
   - Keep runtime behavior local-only until generated selection is wired and tested.
   - This stage represents and generates source-binding, lifetime, and deselection policy only. Persisted source bindings and configuration-change enforcement are implemented in stage 4 after identity links, source-aware grants, and session validity metadata exist.

2. **Immediate security and route repair**
   - Add the Atlas account adapter with signup closed by default.
   - Gate direct local login by selection.
   - Mount required external provider URL patterns and add resolver/integration tests for OIDC login/callback.
   - Correct discovery/issuer configuration naming with a deprecated compatibility mapping for existing `OIDC_ISSUER` deployments.

3. **Atlas authentication gateway and frontend**
   - Add Core-owned config/session/credentials/start/callback operations.
   - Make existing `_allauth` operations policy-enforcing compatibility aliases.
   - Replace frontend allauth discovery with generated/Atlas bootstrap metadata.
   - Implement default-provider redirect, explicit provider choice, sanitized error fallback, and unselected-provider omission.

4. **Provisioning and membership origin**
   - Add provisioning services and audit events.
   - Introduce membership-grant storage; migrate existing membership pairs to manual grants and verify counts/effective access.
   - Switch authorization and membership writers to the effective grant model.
   - Add Principal/Actor/profile policies, source backfill, legacy grant classification, completeness-aware reconciliation, and concurrency protection.
   - Add finite session/grant lifetimes, identity and session revocation, and explicit admin password policy before exposing new gateway paths.

5. **First-party providers on the public contract**
   - Adapt Core local auth to the credential provider contract.
   - Extract OIDC into its first-party provider plugin and remove Core-internal provider-specific claims handling.
   - Add Gitea OAuth2 plugin using the redirect contract.
   - Run the same contract suite against local, OIDC, and Gitea.

6. **Examples and custom credential proof**
   - Add local, Keycloak, Gitea, and minimal custom credential isolated Compose projects.
   - Implement the fixture credential plugin solely against public contracts, document LDAP mapping, and run import-boundary/contract tests.
   - Add fast and integration CI coverage plus secret scanning.

7. **Documentation and release migration**
   - Publish selection, provider, provisioning, group sync, custom provider, reference, security, and troubleshooting pages.
   - Link every guide to an example and validate snippets/routes/config schemas.
   - Announce closed signup, explicit admin recovery, source binding, legacy grant review, finite lifetimes, and authoritative auth selection as migration boundaries with exact examples.

8. **Cleanup after verification**
   - Remove obsolete Core OIDC code and environment-only configuration after the documented compatibility window.
   - Keep or separately deprecate `_allauth` aliases based on observed consumers; do not remove them implicitly in this change's first rollout.

### Rollback

- Preserve AccountAccess, its audit history, and the mandatory Core restriction from the prerequisite. A build that ignores assigned read-only flags is not a safe online rollback target unless affected accounts are blocked or equivalent restrictions remain enforced.
- Before membership-grant migration, schema rollback can retain additive new tables/config columns. Any restored application must still enforce closed signup, explicit admin recovery, source binding and revocation; an older build without these controls is not a safe online rollback target. Use infrastructure recovery rather than reopening it to traffic.
- After membership migration, rollback requires a provided reverse migration that reconstructs one currently effective M2M membership per actor/group grant set, excluding expired/revoked grants; source and expiry detail may be lost, so rollback must be exercised on a backup before production rollout.
- Provider selection generation can roll back to explicit local-only configuration, but signup SHALL remain closed unless an operator consciously restores the old risk.
- OIDC/Gitea/custom provider packages are additive and can be deselected while retaining their identity links and audit history; their sessions/grants are invalidated on deselection.
- A failed external-provider rollout should use a previously selected and tested local break-glass provider or infrastructure recovery procedure; Core must not secretly enable local access when it was not selected.

### Security references

The protocol baseline follows [OAuth 2.0 Security BCP (RFC 9700)](https://www.rfc-editor.org/rfc/rfc9700.html), [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html), and, for a future directory provider, [LDAP authentication (RFC 4513)](https://www.rfc-editor.org/rfc/rfc4513.html) and [OWASP LDAP injection prevention](https://cheatsheetseries.owasp.org/cheatsheets/LDAP_Injection_Prevention_Cheat_Sheet.html). These references guide implementation and negative tests; they do not replace the explicit Atlas requirements above.

## Open Questions

No focused design question blocks implementation. The decisions above fix the gateway prefix, Gitea v1 baseline, diagnostics surface, Standard Catalog collaboration seam, grant-aware administration, source migration format, distributed revocation behavior, expiry predicate, concurrency ordering, and read-only prerequisite contract. Later task groups still own executable adapter, migration, UI, and end-to-end validation.
