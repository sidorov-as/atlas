## Why

`catalog-auth` today is entirely `django-allauth headless` local-account sessions, with permission checks (ownership-based edit) hard-coded per view. `docs/conversation.txt`'s original prompt named SSO as one of the four example plugins from the start ("SSO - как авторизация, тоже"), and `plugin-architecture.md` splits this into Authentication Core (principal identity, sessions, account linking, login/logout, CSRF/security policy — permanently core, ADR 0013) versus Authentication Provider plugins (local, OIDC, SAML, ... — pluggable, keyed collection with a selectable default) plus a separately pluggable policy evaluator behind the core Authorization Service (ADR 0016). `extract-c4-plugin` already introduced a minimal stand-in evaluator and one real permission; this change generalizes both the provider and evaluator stories properly and adds OIDC as the first non-local provider, proving multi-provider deployment (local kept as break-glass) for the first time.

## What Changes

- Split `catalog-auth`'s current allauth-headless integration into Authentication Core (session/CSRF/principal management, provider-agnostic) plus an `atlas.auth.local` provider plugin wrapping the existing allauth-headless username/password flow — behaviorally identical to today, just relocated behind the new provider boundary.
- Add an `AuthenticationProvider` keyed extension point (`plugin-architecture.md:428-442`): a deployment selects one or more providers and a default; `ExternalIdentity` from a provider maps to a stable `Principal` (today's Django `User`/session, formalized as the mapping target).
- Add `atlas.auth.oidc` as a second provider plugin, mapping OIDC claims to a `Principal` without those claims directly becoming authorization decisions (ADR 0013's explicit separation).
- Replace `extract-c4-plugin`'s minimal `AlwaysAllowIfAuthenticated` evaluator with a real pluggable `PolicyEvaluator` singleton extension point; ship a built-in RBAC evaluator implementing today's actual rule (ownership-based edit permission, read unrestricted for any logged-in user) plus `atlas.c4.diagram.read`, as the default selected evaluator — this is a refactor of existing logic into the new shape, not a behavior change.
- Add a claims-mapper concept: an OIDC group claim maps to an Atlas Group/Team membership or role, kept as a distinct step from authentication itself.

## Capabilities

### New Capabilities
- `auth-provider-extension`: Authentication Core owns principal identity, sessions, and login/logout; authentication providers (local, OIDC, ...) are a keyed collection a deployment selects from with a default; external identities map to a stable Principal without directly granting authorization.
- `policy-evaluator-extension`: the Authorization Service delegates decisions to one selected `PolicyEvaluator` singleton; plugins declare namespaced permission ids and request decisions, never implementing a parallel role system.

### Modified Capabilities
- `catalog-auth`: "Session login via allauth headless" is renamed in spirit to "session login via the selected default provider" — for the official distribution with only `atlas.auth.local` selected, behavior is identical (allauth headless, same endpoint), so no scenario text changes; the requirement's mechanism is now provider-mediated. The ownership-based edit permission requirement is unchanged behaviorally but now expressed as a check against the built-in RBAC `PolicyEvaluator` rather than an inline view check.

## Impact

- **Backend**: new `plugins/auth-local/` (or keep local auth as part of Authentication Core if it's judged inseparable from allauth's session mechanics — decide in design.md) and `plugins/auth-oidc/`; new `PolicyEvaluator` extension point replacing change 7's stand-in; `atlas.c4.diagram.read`'s check is repointed at the real evaluator with no behavior change.
- **Behavior preserved**: every `catalog-auth` scenario (session establishment, unauthenticated rejection, ownership-based edit, unrestricted read) must keep passing unmodified against the new provider/evaluator boundary.
- **New capability, not a PoC behavior**: OIDC login itself is net-new (the current PoC has no OIDC), matching `docs/conversation.txt`'s original "SSO" ask; scope it as a working provider, not a fully hardened enterprise SSO integration.
- **Dependents**: `introduce-plugin-distribution-and-composer`'s manifest gains an `auth.providers`/`auth.default` section (already sketched in `plugin-architecture.md:434-440`) that this change's provider selection mechanism must be compatible with.
