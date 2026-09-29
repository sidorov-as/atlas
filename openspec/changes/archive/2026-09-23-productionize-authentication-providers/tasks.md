## 1. Resolve Focused Design Questions

- [x] 1.1 Choose and document the canonical Atlas authentication gateway prefix (`/auth/browser/v1/` or `/_atlas/auth/browser/v1/`) before adding public routes.
- [x] 1.2 Spike the installed/supported Gitea OAuth2 adapter against a pinned Gitea version and record the stable subject field, profile endpoint, required scopes, callback behavior, and whether team synchronization is reliable enough for v1.
- [x] 1.3 Decide whether provider health is represented in the existing plugin health response or a dedicated authentication diagnostics response, preserving provider isolation and redaction.
- [x] 1.4 Define the public collaboration boundary for automatic Actor provisioning with `atlas.standard-catalog` so Core does not import plugin implementation models directly.
- [x] 1.5 Specify how admin/API membership editing displays and removes manual versus provider-managed grants while preserving effective membership from remaining sources.
- [x] 1.6 Record the source binding/migration format, distributed revocation checks, exact-grant expiry queries, and concurrency generation ordering before implementation; do not leave security defaults to provider libraries.


- [x] 1.7 Confirm add-readonly-role is implemented and archived; refresh against its main specs, baseline regression suite, guarded evaluator and custom UserAdmin before authentication work.

## 2. Publish Authentication Provider Contract Types

- [x] 2.1 Add implementation-free provider id, contract version, flow-kind, descriptor, presentation metadata, and remote-logout capability types to `atlas_plugin_api`.
- [x] 2.2 Add normalized external profile, verified identity, redirect challenge, credential input, and safe authentication failure value types with validation for matching provider/source, non-empty stable subjects, attribute provenance, and explicit complete/unavailable/unsupported group snapshots.
- [x] 2.3 Define separate `CredentialAuthenticationProvider` and `RedirectAuthenticationProvider` protocols with minimal flow contexts that expose no Core registries or ORM models.
- [x] 2.4 Add the keyed provider registry and `register_authentication_provider(provider, owner=...)` public function with duplicate-owner diagnostics.
- [x] 2.5 Add public provider lookup/read protocols for Core without exposing unrestricted registry mutation to plugins.
- [x] 2.6 Extend `PluginDescriptor` with static, Django-safe authentication provider contributions and verify descriptors import before `django.setup()` with no database/network access.
- [x] 2.7 Export matching safe provider-presentation/bootstrap types from `@atlas/plugin-api` or the chosen Core-owned TypeScript contract module.
- [x] 2.8 Update Plugin API `__all__`, typing tests, API documentation, and semver/compatibility notes for `atlas.auth.providers.v1`.
- [x] 2.9 Extend import-boundary rules so auth plugins may use the published contracts but may not import Core auth registries, settings, models, session helpers, or undocumented allauth internals.

## 3. Build the Provider Contract-Test Kit

- [x] 3.1 Add reusable credential-provider contract tests for descriptor identity, normalized success, invalid credentials, exception sanitization, stable subject behavior, and credential non-persistence.
- [x] 3.2 Add reusable redirect-provider contract tests for start challenge, callback correlation, mismatched/replayed state, normalized success, and sanitized upstream failure.
- [x] 3.3 Add common contract tests rejecting empty subjects, provider-id mismatch, authorization-bearing results, session establishment by provider code, and invalid flow metadata.
- [x] 3.4 Make the contract-test kit consumable by separately packaged plugins without repository-private fixtures.
- [x] 3.5 Document provider-specific fixture/factory hooks and add a minimal out-of-tree-style test package proving the test kit can run independently.
- [x] 3.6 Add contract fixtures for source mismatch, unverified restricted attributes, missing/partial/complete-empty groups, empty credentials, oversized results, and isolated provider failures.
- [x] 3.7 Add simultaneous callback consumption, expired/browser-mismatched state, and session-fixation tests; document which protocol-specific tests adapter authors must supply.


## 4. Make Manifest Authentication Authoritative

- [x] 4.1 Replace string-only auth provider selection with ordered policy-bearing provider entries while preserving clear migration validation for the legacy schema.
- [x] 4.2 Add manifest models for default provider, local signup policy, Principal provisioning, Actor provisioning, provider-managed profile fields, group-sync mode, completeness/freshness, explicit mappings, restricted-attribute assurance, source bindings, finite session lifetime, admin break-glass allowlist, origin/outbound trust, and password/recovery policy.
- [x] 4.3 Validate non-empty selection, unique ids, selected default, provider descriptor existence, owning artifact presence, flow compatibility, supported policy values, and Plugin API/Core compatibility.
- [x] 4.4 Extend lock models and resolver output with deterministic non-secret auth selection, provider metadata, and Core policy.
- [x] 4.5 Assert resolved secrets, submitted credentials, and token values can never serialize into the lock.
- [x] 4.6 Generate backend selected-auth configuration from the lock, including provider order/default and Core provisioning policies.
- [x] 4.7 Generate frontend-safe auth bootstrap inputs containing only selected presentation metadata and default behavior.
- [x] 4.8 Update composer diff/validation messages to give exact migration guidance for empty legacy auth fields, missing providers, duplicate ids, and unselected defaults.
- [x] 4.9 Update the checked-in official distribution manifest and lock to explicitly select local auth, disable signup, and preserve conservative manual provisioning.
- [x] 4.10 Add manifest, resolver, lock, generation, reproducibility, compatibility, and secret-leak tests for local-only, OIDC-only, multi-provider, and custom-provider selections.
- [x] 4.11 Validate finite positive lifetimes, default disabled admin password login, explicit active-staff id allowlist shape, allowed destinations/public origin, supported assurance policies, and development-only fixture exceptions.


## 5. Harden Local Authentication and Signup

- [x] 5.1 Implement an Atlas allauth account adapter whose server-side `is_open_for_signup()` reads authoritative generated policy and defaults to closed.
- [x] 5.2 Configure the adapter in Django settings and test direct signup through both the current allauth route and the new Atlas gateway.
- [x] 5.3 Gate local catalog login on selection of `atlas.auth.local`, including direct calls that bypass the frontend.
- [x] 5.4 Default admin password login to disabled; implement explicit break-glass mode with active staff Principal allowlisting, Core session validity/audit/rate limiting, and tests from admin login through catalog API access.
- [x] 5.5 Add explicit local signup opt-in behavior and safe public `signupOpen` metadata when local is selected.
- [x] 5.6 Add or update a supported management command for idempotent first-administrator bootstrap using non-logged secret input.
- [x] 5.7 Add rate-limit/Axes regression tests for local credential failures without username-existence disclosure.
- [x] 5.8 Add release-facing migration tests proving previously implicit signup is rejected by default and creates no User, Actor, link, or session.
- [x] 5.9 Configure shared password validators for bootstrap/signup/change/reset with a fifteen-character default minimum, long-password support, common/similarity rejection, and no truncation.
- [x] 5.10 Gate public reset and account-management compatibility endpoints on explicit recovery policy; test verified recovery addresses, one-use expiry, generic failures, throttling, and session revocation after reset.


## 6. Implement the Atlas Authentication Gateway

- [x] 6.1 Add the canonical versioned provider config endpoint backed by generated selection rather than allauth provider discovery.
- [x] 6.2 Add Core-owned session read/delete operations retaining existing Django session and CSRF semantics.
- [x] 6.3 Add selected credential-provider invocation with flow-kind validation, safe error categories, and Core-owned session establishment.
- [x] 6.4 Add selected redirect-provider start behavior with safe return-URL validation and provider/source/browser-bound, expiring state and a Core-issued attempt generation.
- [x] 6.5 Add selected redirect-provider callback behavior with correlation/replay validation before provisioning.
- [x] 6.6 Reject unselected, unknown, disabled, or wrong-flow provider invocations without running provider code.
- [x] 6.7 Route existing `/_allauth/browser/v1/*` compatibility operations through equivalent selection and signup enforcement so they cannot bypass policy.
- [x] 6.8 Mount the required allauth provider URL patterns for the transitional OIDC/Gitea implementations and add resolver tests for login/callback names.
- [x] 6.9 Add safe structured authentication errors and correlation ids shared by credential, redirect, provisioning, and logout stages.
- [x] 6.10 Add API tests for config, session, CSRF, credential success/failure, redirect start/callback, unsafe return URLs, replay, unselected providers, and compatibility aliases.
- [x] 6.11 Implement session-id rotation, production cookie flags, non-cacheable auth responses, trusted public-origin/proxy handling, and CSRF/origin enforcement on login/signup/start/logout.
- [x] 6.12 Audit every mounted allauth/admin/provider account route, including password reset, account connection and internal callbacks, for equivalent selection, linking, recovery, and session-validity policy.


## 7. Implement Default Provider and Fallback UX

- [x] 7.1 Replace frontend allauth provider discovery with the Atlas authentication bootstrap contract.
- [x] 7.2 Render the standard credential form only for selected credential providers and submit to the selected provider-specific gateway operation.
- [x] 7.3 Render selected redirect providers from presentation metadata without constructing provider-library routes in frontend code.
- [x] 7.4 Auto-start a sole or default redirect provider on first unauthenticated login entry.
- [x] 7.5 Add the permanent explicit provider-choice path/query mode that suppresses automatic redirect.
- [x] 7.6 Detect sanitized redirect/provider failures and offer selected fallback providers without redirect loops.
- [x] 7.7 Preserve the originally requested safe application path across successful local or external login.
- [x] 7.8 Ensure OIDC-only/OAuth-only deployments expose no local form or signup affordance.
- [x] 7.9 Add frontend tests for local-only, redirect-only, local-default multi-provider, redirect-default multi-provider, unselected provider omission, fallback, and loop prevention.
- [x] 7.10 Add representative browser tests covering local login and redirect-default failure-to-local-fallback.

## 8. Introduce Source-Aware Group Membership Grants

- [x] 8.1 Design and add the membership-grant model with Actor, Group, source kind, external identity link, external key, legacy-unclassified marker, expiry, creation/confirmation timestamps, and uniqueness/indexes.
- [x] 8.2 Add a data migration that converts every existing Group-member pair into an equivalent legacy-unclassified manual grant without changing effective access.
- [x] 8.3 Add migration invariants comparing pre/post actor-group pair counts and rejecting duplicate or orphaned grant state.
- [x] 8.4 Implement the shared effective-membership query/service used by authorization, serializers, admin, ingestion, and provider reconciliation.
- [x] 8.5 Update `PolicyEvaluator` ownership membership checks to use effective grants and add regression tests across every registered entity kind.
- [x] 8.6 Update manual membership creation/removal paths to manipulate only manual grants and preserve provider grants.
- [x] 8.7 Update admin/UI/API membership presentation to expose effective membership and its source grants according to the resolved design.
- [x] 8.8 Add tests for simultaneous manual and multiple external-identity grants, removal of one source, preservation of remaining access, and complete removal after the final grant disappears.
- [x] 8.9 Provide and test a reverse migration/rollback transformation that restores one legacy effective membership per actor/group pair.
- [x] 8.10 Add audited dry-run and apply commands to classify legacy grants or transfer reviewed grants to an identity link without leaving duplicate manual access; require classification or explicit retained-grant acknowledgement before exact activation.
- [x] 8.11 Enforce exact-grant expiry in all effective-membership reads, applying shortened configured freshness and provider/source deselection to existing grants; test a live session from another provider, expiry without a cleanup job, deselection, and preservation of independently valid grants.
- [x] 8.12 Test migration from old OIDC-added memberships through source classification and exact removal, plus reverse migration and documented loss of provenance.


## 9. Build Core Provisioning and Reconciliation Services

- [x] 9.1 Move external identity linking behind an atomic Core provisioning service with provider/source/subject validation, database uniqueness, revocation markers, and collision handling without email/username auto-linking.
- [x] 9.2 Implement `preprovisioned`, `automatic`, and `restricted` Principal provisioning with verified-attribute/domain restrictions checked on every login, including existing Principals.
- [x] 9.3 Implement explicit provider-managed profile-field allowlists and preserve operator-managed fields; exclude active/read_only/admin/password/link/recovery security fields from the selectable profile allowlist.
- [x] 9.4 Publish and implement the resolved Standard Catalog collaboration contract for `manual` and `automatic` Actor provisioning/linking, including existing Principals without an Actor.
- [x] 9.5 Prevent automatic Actor provisioning from silently claiming similar unlinked Actors; implement and test the selected collision behavior.
- [x] 9.6 Implement explicit external-group normalization and mapping to existing Atlas Groups with unknown groups ignored by default.
- [x] 9.7 Implement `none`, `additive`, and atomic `exact` reconciliation using source-aware grants.
- [x] 9.8 Ensure exact sync removes only stale grants owned by the authenticating external identity link and preserves manual/other-provider access.
- [x] 9.9 Define and implement fail-closed transaction behavior for link/provision/profile/group errors before session creation.
- [x] 9.10 Add audit events for Principal/Actor creation, link conflicts, profile updates, grant additions/removals, and provisioning failures with central secret/token/claim redaction.
- [x] 9.11 Add tests for every provisioning/reconciliation mode, repeated login, profile changes, unknown groups, link collisions, rollback on partial failure, and audit redaction.
- [x] 9.12 Implement operator identity inspect/link/revoke/restore/source-migrate commands with exact identifiers, safe preview, privileged-target option, audit, and revocation markers preventing automatic reprovisioning.
- [x] 9.13 Serialize per-Principal/link updates and reject stale Core attempt generations; test concurrent first login, repeated callback, older snapshots finishing last, and revoke-versus-login races.
- [x] 9.14 Move denial/conflict/failure security-event emission outside rolled-back provisioning transactions and test durable safe failure visibility alongside atomic success audit.
- [x] 9.15 Reject incomplete exact snapshots, renew expiry only from complete snapshots, and test unavailable/partial/empty data plus removal of the last effective grant.
- [x] 9.16 Test restricted eligibility loss for existing users, verified domain normalization, profile impersonation, protected-field preservation including read_only, and automatic Actor creation for an existing Principal.
- [x] 9.17 Persist provider/source binding records with non-secret configuration fingerprints, lock digests, activation/revocation timestamps, and generations; require a new namespace or reviewed migration when authority changes so existing links and grants cannot be silently reused.


## 10. Move Built-In Providers onto the Public Contract

- [x] 10.1 Adapt `atlas.auth.local` to the credential-provider descriptor/runtime contract while retaining all current valid-login/session tests.
- [x] 10.2 Create a first-party `atlas.auth.oidc` plugin package with static descriptor, typed config schema, runtime registration, dependencies, and distribution artifacts.
- [x] 10.3 Rename OIDC connection configuration to `discoveryUrl` plus explicit `expectedIssuer`, with validated compatibility handling and migration diagnostics for existing `OIDC_ISSUER` deployments.
- [x] 10.4 Configure OIDC scopes, userinfo/ID-token normalization, issuer-bound stable `sub`, Code/PKCE S256/nonce, signature/algorithm/issuer/audience/authorized-party/time validation, UserInfo sub equality, callback state, trusted JWKS rotation, and optional remote logout behind the redirect contract.
- [x] 10.5 Remove provider-specific group mutation from allauth signals; return normalized external groups and delegate all mapping/reconciliation to Core.
- [x] 10.6 Move existing OIDC ExternalIdentityLink behavior into the shared provisioning pipeline with operator-verified historical-source backfill and no silent reassignment; block ambiguous legacy links until reviewed.
- [x] 10.7 Run the public credential contract suite against local and redirect contract suite against OIDC.
- [x] 10.8 Add OIDC integration tests with a deterministic fake provider for discovery, authorization, token exchange, UserInfo sub mismatch, PKCE/nonce/token-time/algorithm/signature/issuer/audience/state failures and JWKS rotation, provisioning, session, and logout.
- [x] 10.9 Remove obsolete Core OIDC registry/config/signal code only after the plugin-backed path and data compatibility tests pass.

## 11. Add the Gitea OAuth2 Provider

- [x] 11.1 Create the first-party `atlas.auth.gitea` provider plugin package with descriptor, typed namespaced config, secret reference, and redirect runtime registration.
- [x] 11.2 Implement Gitea authorization/token/profile behavior using the validated established adapter/library behind the public redirect contract.
- [x] 11.3 Normalize the spiked stable Gitea subject and supported profile fields and explicitly configure group sync as `none` unless reliable team semantics were proven.
- [x] 11.4 Add safe errors, timeouts, state/replay behavior, health diagnostics, and documented local logout/optional remote logout semantics.
- [x] 11.5 Run the shared redirect provider contract suite and provider-specific unit/integration tests.
- [x] 11.6 Add composition tests confirming Gitea appears only when its plugin is selected and configured and that OAuth scopes never directly grant Atlas permissions.
- [x] 11.7 Prove Gitea Code/PKCE S256 support and source-bound subject stability against the selected pinned version; block unsupported combinations rather than downgrade the baseline.


## 12. Centralize Authentication Security and Diagnostics

- [x] 12.1 Implement one redaction utility/policy covering provider configuration, credentials, authorization codes, access/refresh/ID tokens, LDAP bind data, and raw upstream bodies.
- [x] 12.2 Apply redaction to config repr/serialization, validation errors, provider exceptions, audit events, structured logs, health output, and user-facing errors.
- [x] 12.3 Add bounded connection/read timeouts and provider-specific rate limiting to external authentication operations.
- [x] 12.4 Implement safe provider health checks according to the resolved health endpoint decision and isolate one provider's outage from alternatives.
- [x] 12.5 Surface exact callback URLs, provider ids, selection/default state, and safe failure categories through operator diagnostics without revealing secrets.
- [x] 12.6 Record establishing provider/source/link, authentication time, and Principal revocation generation for session validity and logout/diagnostics; never use them to grant permissions.
- [x] 12.7 Implement local-first logout and optional provider remote logout such that upstream failure cannot restore the Atlas session.
- [x] 12.8 Add security regression tests and log-capture assertions proving credentials, tokens, secrets, raw claims, and upstream bodies never escape.
- [x] 12.9 Implement the default eight-hour absolute session deadline and per-request validity checks across Core, plugins and admin; apply shortened configured lifetimes immediately to existing sessions and test expiry unaffected by activity.
- [x] 12.10 Persist selected-auth policy/source generations and enforce Principal revoke-all, inactive/blocked checks, source/link revocation, withdrawn admin allowlisting, and configuration-change/deselection invalidation for existing sessions and grants across workers, including in-flight login races and non-resurrection after reselect/rollback.
- [x] 12.11 Apply verified TLS, bounded deadlines/response sizes, and destination/DNS/redirect validation to identity requests; test internal allowlisted IdPs, unexpected discovery endpoints, metadata-address rejection, and no insecure retry.
- [x] 12.12 Disable default framework token persistence, define bounded protected retention only when remote logout needs it, and cover DB/session/browser/tracing/proxy callback-log leak checks.
- [x] 12.13 Apply shared rate limits across workers and aliases with trusted client-address handling and account/provider/deployment budgets; test that switching providers or compatibility routes cannot bypass aggregate limits.


## 13. Add the Local Authentication Example

- [x] 13.1 Create `examples/authentication/README.md` with a provider/topology selection matrix, resource expectations, security disclaimers, and links.
- [x] 13.2 Create the isolated `examples/authentication/local/compose.yaml` and `.env.example` using local-only auth and closed signup.
- [x] 13.3 Add controlled disposable admin bootstrap and sample Actor/Group linkage without committing a production password.
- [x] 13.4 Write the local README with architecture, commands, credentials policy, Principal/Actor/Group explanation, allowed/denied verification, logout, troubleshooting, cleanup, and production differences.
- [x] 13.5 Add Compose rendering and smoke tests for signup rejection, local login, authenticated API access, denied non-owner write, and logout.

## 14. Add the Keycloak OIDC Example

- [x] 14.1 Create `examples/authentication/oidc-keycloak/compose.yaml`, `.env.example`, pinned Keycloak service, health checks, volumes, and startup ordering.
- [x] 14.2 Add an importable disposable Keycloak realm with Atlas client, exact callback/origins, scopes/mappers, test users, and test groups.
- [x] 14.3 Configure Atlas as OIDC-only by default with automatic Principal/Actor provisioning and demonstrable exact group synchronization.
- [x] 14.4 Document how to add explicit local break-glass selection without silently enabling signup.
- [x] 14.5 Write the README covering discovery, issuer, callback, claims, provisioning, group removal, permission checks, Atlas-versus-IdP logout, troubleshooting, cleanup, and production caveats.
- [x] 14.6 Add smoke/browser coverage for OIDC redirect/callback, stable repeat login, exact membership removal, denied unmapped group, session logout, and no local form.

## 15. Add the Gitea OAuth2 Example

- [x] 15.1 Create `examples/authentication/oauth2-gitea/compose.yaml`, `.env.example`, pinned Gitea service, health checks, volumes, and startup ordering.
- [x] 15.2 Add repeatable Gitea bootstrap for the disposable user and OAuth application without committing a non-disposable generated secret.
- [x] 15.3 Configure Atlas with the selected `atlas.auth.gitea` adapter and the provider policies proven by the Gitea spike.
- [x] 15.4 Write the README explaining provider-specific identity, required scopes, stable subject, callback, provisioning, manual membership when teams are unsupported, logout, troubleshooting, cleanup, and why this is not generic OAuth identity.
- [x] 15.5 Add smoke/browser coverage for authorization, callback, stable repeat login, normal Atlas session, absence of scope-derived permissions, and logout.

## 16. Prove the Custom Credential Contract and Document LDAP Mapping

- [x] 16.1 Create a separately packaged development-only fixture credential plugin under `examples/authentication/custom-credentials/plugin/` using public SDK imports only.
- [x] 16.2 Implement deterministic disposable users with stable source/subject, non-empty password verification, profile assurance, and explicit complete/unavailable group fixtures; gate fixture use on development configuration.
- [x] 16.3 Run the public credential contract suite and import-boundary checks against the example package.
- [x] 16.4 Create an isolated Atlas/PostgreSQL Compose topology without an external directory dependency.
- [x] 16.5 Demonstrate automatic Principal/Actor provisioning, exact complete/empty snapshots, unavailable-group rejection, and fallback through Core policy.
- [x] 16.6 Write the runnable custom tutorial and a separate LDAP mapping covering every SDK input/result, typed secrets, deadlines, source/UUID, assurance, TLS validation, filter/DN escaping, empty/anonymous/ambiguous bind rejection, and complete group pagination; explicitly state that no production LDAP implementation ships.
- [x] 16.7 Add smoke tests for valid/invalid/empty credentials, account-existence indistinguishability, simulated outage with healthy fallback, stable repeated login, provisioning, group freshness, redaction, and logout.

## 17. Expand Authentication Documentation

- [x] 17.1 Add the operator authentication overview and decision matrix distinguishing local, OIDC, provider-specific OAuth2, custom providers, browser sessions, and unsupported API bearer/SAML capabilities.
- [x] 17.2 Update local authentication guidance for authoritative selection, signup closed by default, bootstrap/recovery, admin boundary, Actor linking, fallback, and the local example.
- [x] 17.3 Rewrite OIDC guidance around discovery URL, expected issuer, exact callback, client/secret, scopes/claims, provisioning, reconciliation, fallback, logout, diagnostics, and the Keycloak example.
- [x] 17.4 Add provider-specific OAuth2/Gitea guidance that explicitly rejects the generic OAuth-as-identity assumption and links to the Gitea example.
- [x] 17.5 Add dedicated Principal/Actor/profile provisioning and Group membership reconciliation guides with mode tables, ownership sources, audit behavior, and safe migration advice.
- [x] 17.6 Expand authentication/identity and permissions concepts to cover External Identity, membership grants, provider-managed state, administrative flags, Purge Grants, sessions, and authorization separation.
- [x] 17.7 Add the custom authentication provider SDK guide and minimal custom credential tutorial plus LDAP implementation mapping covering flow selection, two-phase lifecycle, config/secrets, normalized results, tests, packaging, and compatibility.
- [x] 17.8 Update manifest, environment/configuration, Plugin API, route/error, management command, and provider diagnostics reference pages.
- [x] 17.9 Expand symptom-oriented troubleshooting for composition, missing provider, closed signup, disabled local login, callback/discovery/issuer, CSRF/origin, outage, identity collision, missing Actor, stale/exact membership, and logout.
- [x] 17.10 Update documentation navigation, landing pages, cross-links, README entry points, and release/migration notes without duplicating canonical procedures.
- [x] 17.11 Document source migration, link administration/revocation, legacy-grant classification, additive versus exact freshness, session/revoke-all bounds, admin-to-catalog break-glass access, and the absence of immediate upstream deprovisioning.
- [x] 17.12 Document trusted-code plugin boundaries, protected origin/outbound policy, password/recovery settings, and token/log retention using source-validated examples.
- [x] 17.13 Apply $humanizer skill to every *.md file you have changed during task 17.


## 18. Validate Examples, Documentation, and Release Safety

- [x] 18.1 Extend documentation validation to check provider ids, manifest/config snippets, environment names, callback routes, navigation, and links against source contracts.
- [x] 18.2 Add fast CI for every example's YAML/JSON/fixture parsing, `docker compose config`, config schema validation, docs commands, import boundaries, and secret scanning.
- [x] 18.3 Add required integration CI jobs that start and smoke-test local, Keycloak, Gitea, and custom credential topologies with diagnostic artifact capture that remains secret-safe.
- [x] 18.4 Add release-gating browser coverage for representative credential, redirect, default/fallback, provisioning, authorization, and logout journeys.
- [x] 18.5 Run backend unit/API/integration suites, frontend unit/browser suites, composer tests, Plugin API tests, import-boundary checks, migrations, docs build, and example validation; fix only failures caused by this change.
- [x] 18.6 Run static typing, linting, formatting, migration-boundary checks, and strict OpenSpec validation for all touched packages and artifacts.
- [x] 18.7 Exercise forward and reverse membership migrations against representative manual and provider grant data and document backup/rollback boundaries.
- [x] 18.8 Verify no secret/credential/token/raw-claim value appears in manifests, locks, generated modules, frontend assets, bootstrap responses, logs, health output, test snapshots, or committed example files.
- [x] 18.9 Verify the official distribution starts with its explicit auth policy, local login remains available, anonymous signup is closed, protected APIs require a session, and existing authorization behavior is unchanged.
- [x] 18.10 Produce the final operator migration checklist for existing local-only and experimental OIDC deployments, including manifest edits, environment renames, callback updates, signup behavior, data migration, rollback, and fallback verification.
- [x] 18.11 Add release-gating negative journeys for issuer replacement, unverified restricted email, inactive user and session revocation, admin password bypass, incomplete groups, legacy exact migration, and concurrent authentication.
- [x] 18.12 Verify the default fixture example needs no OpenLDAP service while the documented LDAP flow maps entirely onto public v1 contract types.


## 19. Preserve Read-Only Integration from the Prerequisite

- [x] 19.1 Retain the mandatory Core write guard and public guarded evaluator across gateway, compatibility routes, direct mutation guards and effective-membership refactoring; do not encode read-only inside is_group_member.
- [x] 19.2 Preserve AccountAccess and audit state across UserAdmin integration, identity/link/source operations, provisioning and forward/reverse membership migrations; reconcile migration dependencies without dropping or resetting the side-car.
- [x] 19.3 Preserve isReadOnly loading and refresh after every login/callback, on focus/visibility and mutation-route entry, and after write denial; retain fail-safe loading/error behavior.
- [x] 19.4 Add combined regression tests for repeated local/external login, role-like claims/profile updates, another linked provider, and newly added manual/provider grants while read_only remains unchanged.
- [x] 19.5 Test read-only superuser/Purge Grant holders and allowlisted admin break-glass sessions against direct catalog/admin mutations, own-flag changes, and user-triggered job enqueueing with no side effects.
- [x] 19.6 Test flag on/off in an existing external session: next authorization reflects current state, stale UI cannot bypass it, and clearing the flag restores ordinary permissions only.
- [x] 19.7 Document and exercise the operator workflow that prepares a flagged Principal, links its exact identity, and enables preprovisioned access; verify missing-link denial and first-login read success/write rejection.
- [x] 19.8 Run the prerequisite's full read-only regression suite with the new authentication stack and effective grants, including a permissive selected evaluator; treat regressions as release blockers and include AccountAccess preservation in rollback verification.
