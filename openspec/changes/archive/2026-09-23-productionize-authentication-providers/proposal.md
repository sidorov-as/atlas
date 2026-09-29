## Why

Atlas's authentication architecture promises selectable local and external providers, but the current implementation is not yet safe or complete for operator use: manifest auth selection is parsed but ignored, local signup remains callable, the OIDC callback routes are absent, the default provider is hard-coded, external group synchronization is only additive, and third-party providers cannot integrate without importing Core internals. Operators also lack runnable, self-contained examples that demonstrate how identities, Actors, Groups, secrets, callbacks, and fallback access behave end to end.

This change turns authentication into a production-ready, documented extension surface: deployments can select and default providers safely, local/OIDC/provider-specific OAuth flows work consistently, identity provisioning and group reconciliation are explicit policies, third parties can implement credential or redirect providers through a versioned Plugin API, and maintained Compose examples make each supported topology inspectable and reproducible.

## What Changes

- Make `auth.providers` and `auth.default` in the distribution manifest authoritative runtime inputs, validate them during composition, preserve them in the lock, and generate backend/frontend authentication selection configuration.
- Close local self-signup by default through an Atlas-owned allauth policy adapter; hiding UI or omitting documentation SHALL NOT be treated as the security control. Permit an explicit operator opt-in where a deployment intentionally supports self-registration.
- Ensure direct requests cannot use an unselected authentication provider, even when its dependency is installed or its generic allauth endpoint exists.
- Register stable external-provider login/callback routes whenever a selected redirect provider requires them, independent of which provider is the default.
- Implement default-provider UX for local-only, external-only, and multi-provider deployments, including an explicit provider-choice/fallback route that prevents redirect loops and preserves break-glass access when configured.
- Correct and harden OIDC configuration around discovery URL, issuer validation, callback URL, scopes, secret handling, stable subject mapping, and operator diagnostics.
- Add a supported provider-specific OAuth2 login implementation and example using Gitea; document that OAuth 2.0 alone does not define identity, userinfo, or groups and that each OAuth provider requires a provider-specific adapter.
- Introduce explicit policies for Principal provisioning, Actor provisioning/linking, external Group mapping, unknown-group handling, and additive versus exact membership reconciliation. Authentication attributes SHALL never directly grant Atlas permissions or administrative status.
- Publish a versioned `atlas.auth.providers.v1` keyed extension contract through `atlas_plugin_api`, with separate credential and redirect flow protocols, normalized verified-identity results, registration APIs, error contracts, health behavior, and contract-test helpers.
- Keep Authentication Core responsible for session establishment, CSRF policy, logout, external-identity linking, provisioning, and authorization handoff; custom providers remain responsible only for securely verifying their protocol or credentials and returning a normalized identity.
- Add a minimal separately packaged custom credential provider example using disposable fixture identities and only public Plugin API contracts. Strictly define how a future LDAP search-and-bind provider uses that contract, without requiring a production LDAP plugin or OpenLDAP topology in this change.
- Add a top-level `examples/authentication/` collection with isolated Compose projects and README guides for local authentication, Keycloak OIDC, Gitea OAuth2, and a custom credential fixture provider.
- Expand operator, concept, reference, plugin-author, security, provisioning, group-sync, and troubleshooting documentation so readers can choose an authentication method and understand precisely how Users/Principals, Actors, Groups/Teams, sessions, claims, logout, and fallback access behave.
- Add automated contract, integration, browser-flow, Compose validation, documentation, and secret-leak checks covering every supported provider topology.

- Bind external identities and grants to an immutable authority/source namespace; provide audited link administration, trusted restricted-eligibility rules, concurrency guarantees, and explicit legacy membership classification.
- Bound session validity and exact-grant freshness (eight-hour defaults), support local emergency revocation, and make admin password break-glass an explicit disabled-by-default exception whose sessions can also access catalog APIs.
- Require complete group snapshots and fail-closed provisioning; specify OAuth/OIDC protocol checks, production transport/origin/session protections, local password/recovery policy, and secret-safe token/log retention.

## Integration prerequisite

`add-readonly-role` was implemented and archived as `2026-09-20-add-readonly-role` before this change entered implementation. This plan has been refreshed against its main specs and implementation. It consumes the resulting AccountAccess model, mandatory Core write restriction, guarded evaluator, operator management/audit, custom UserAdmin, and current-user access-state contract; it does not introduce a second read-only mechanism.

Authentication, identity linking, provisioning, membership-grant migrations, and admin break-glass must preserve AccountAccess and the Core restriction. The gateway/frontend refactor retains `isReadOnly` and its refresh behavior. Integration acceptance includes issuing preprovisioned external read-only accounts before first access and proving that new providers or grants cannot restore write access.

## Capabilities

### New Capabilities

- `authentication-provider-sdk`: Public, versioned contracts and lifecycle rules for third-party credential and redirect authentication providers, including registration, normalized identity results, endpoint behavior, failure isolation, health, and contract testing.
- `authentication-provisioning`: Operator-selectable policies for source-bound external identity linking, revocation, trusted eligibility, Principal and Actor creation/linking, profile updates, Group mapping, unknown-group behavior, and additive or exact membership reconciliation.
- `authentication-examples`: Runnable and CI-validated Compose examples for local auth, Keycloak OIDC, Gitea OAuth2, and a minimal custom credential provider, each with complete operational documentation and disposable fixtures.

### Modified Capabilities

- `auth-provider-extension`: Make provider selection/defaulting real, distinguish credential and redirect flows, define provider routing and fallback behavior, and preserve provider-independent sessions and authorization.
- `catalog-auth`: Close local signup by default, reject unselected local login, define authenticated-session behavior across provider types, and retain centralized authorization semantics.
- `deployment-manifest-and-lock`: Validate, lock, and generate runtime authentication selection, default-provider, provisioning, and synchronization configuration.
- `plugin-configuration-isolation`: Apply typed namespaced configuration, secret references, public projections, and leak prevention to every built-in and third-party authentication provider.
- `core-plugin-contract-surface`: Publish authentication provider registration and Core-owned provisioning/session collaboration services instead of requiring Core-internal imports.
- `plugin-contract-packages`: Version and export the Python/TypeScript authentication provider contract types and their contract-test support.
- `documentation-site-experience`: Add task-oriented authentication selection, provisioning, custom-provider, example, security, and troubleshooting documentation backed by validated source examples.

## Impact

- **Backend/Core:** authentication registry, allauth adapters and URL routing, settings generation, session establishment, external identity models/services, provisioning, group reconciliation, diagnostics, and API/bootstrap responses.
- **Frontend:** login/provider-choice behavior, default-provider redirect and fallback handling, provider presentation metadata, error recovery, and tests.
- **Composer/distributions:** manifest and lock schema validation, generated selected-auth configuration, provider compatibility checks, and the official distribution's explicit auth policy.
- **Plugin API:** new versioned Python contracts, registration functions, normalized identity/provisioning collaboration types, and a provider contract-test kit; optional TypeScript presentation types for frontend bootstrap consumption.
- **Built-in providers:** local and OIDC move onto the same published provider model; a provider-specific Gitea OAuth2 implementation is added without claiming generic OAuth identity interoperability.
- **Examples/dependencies:** new Compose topologies may introduce Keycloak, Gitea, and a sample custom credential plugin as development/example-only dependencies.
- **Documentation/CI:** navigation and reference updates, runnable configuration examples, Compose parsing and smoke tests, authentication flow tests, callback/route checks, and assertions that secrets never reach locks, frontend config, generated artifacts, or logs.
- **Operational behavior:** **BREAKING** for deployments that implicitly relied on the currently exposed local signup endpoint; signup becomes disabled unless explicitly enabled. Deployments must also declare selected/default providers once manifest auth selection becomes authoritative.

Existing external identity links require verified source backfill. Legacy memberships remain access-preserving manual grants until classified; exact sync does not silently take ownership of them. Admin password access requires explicit opt-in/allowlisting, sessions become bounded and revocable, and production transport/password policy may reject previously permissive configurations. These are documented migration boundaries.
