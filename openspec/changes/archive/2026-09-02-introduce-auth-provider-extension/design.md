## Context

`catalog-auth` today is `django-allauth headless` wired directly into `server.apps.catalog`'s settings (`INSTALLED_APPS` includes `allauth`, `allauth.account`, `allauth.headless` per `backend/server/settings/components/common.py:32-34`), with the ownership-based edit permission check presumably inline in `api/permissions.py`. `extract-c4-plugin` (change 7) needed *a* permission check to exist and deliberately used a minimal always-allow stand-in rather than block on this change. `plugin-architecture.md`'s Authentication and authorization section (lines 426-457) and ADR 0013/0016 define the target split precisely.

## Goals / Non-Goals

**Goals:**
- Authentication Core (principal/session/CSRF/security policy) is provider-agnostic; providers are a keyed extension point with a selectable default.
- `atlas.auth.local` (wrapping today's allauth-headless flow) and `atlas.auth.oidc` both exist and are independently selectable; the official distribution keeps `atlas.auth.local` as at least a break-glass option even when OIDC is the default.
- `PolicyEvaluator` is a real singleton extension point; the built-in RBAC evaluator reproduces today's exact ownership-based rule plus `atlas.c4.diagram.read`.
- Every `catalog-auth` scenario passes unmodified.

**Non-Goals:**
- SAML or LDAP providers — `plugin-architecture.md` names them as examples, not requirements; this change ships local + OIDC only.
- An OPA-backed `PolicyEvaluator` — the built-in RBAC evaluator is the only one shipped; OPA is named as a future option, not built here.
- A UI for switching/configuring providers at runtime — provider selection is deployment-manifest-driven (config, not a runtime admin feature), consistent with this whole program's operator-controlled composition principle.
- Building the full claims-mapper as a generalized rules engine — a minimal, direct claim-to-Group mapping is enough to prove the separation between "who is this" (authentication) and "what can they do" (authorization via Group membership → RBAC).

## Decisions

**`atlas.auth.local` stays a thin plugin wrapping allauth-headless, not a full reimplementation.** Django-allauth already does session/CSRF/credential handling well; the architectural change is *where the seam is* (Authentication Core calls into a selected provider for the login transaction, rather than allauth being wired directly into top-level settings), not replacing allauth. Authentication Core owns the parts allauth doesn't need to own per-provider: session lifecycle after login, principal resolution, logout, CSRF policy shared across all providers.

**`Principal` is the existing Django `User` model, not a new table.** `plugin-architecture.md:441-442` says an external identity maps to "a stable Atlas principal" — today's `User` already is that stable identity for local accounts; OIDC's `ExternalIdentity` (issuer + subject claim) gets its own small mapping table (`ExternalIdentityLink`: `user`, `provider_id`, `external_subject`) pointing at the same `User`, rather than introducing a parallel identity concept.

**`PolicyEvaluator` is `Protocol: def check(principal, permission: str, resource: CatalogEntity | None) -> bool`.** Matches `plugin-architecture.md:449-453`'s call shape (`authorization.check(principal=..., permission=..., resource=...)`) exactly. The built-in RBAC evaluator implements `check` by: superuser → always true; permission is a read permission → true for any authenticated principal (today's "read access unrestricted" rule); permission is `<kind>.edit` → true iff principal is a member of `resource.owner`; `atlas.c4.diagram.read` → true for any authenticated principal (unchanged from change 7's stand-in, now served by the real evaluator instead of a special-cased always-allow).

**OIDC claims mapping is a distinct step run *after* successful OIDC authentication, writing Group membership, not evaluated inline during `PolicyEvaluator.check`.** Keeps the "SSO claims do not directly become authorization decisions" separation (`plugin-architecture.md:442`) literal: by the time `PolicyEvaluator.check` runs, OIDC has already resolved to a `Principal` with ordinary Group memberships indistinguishable from a locally-created user's.

## Risks / Trade-offs

- [Splitting allauth-headless's currently-monolithic settings integration into "Authentication Core calls a selected provider" risks subtly changing session/CSRF timing] → Keep this the very first sub-step (move-not-rewrite of `atlas.auth.local`), fully verified against every `catalog-auth` session/CSRF scenario, before adding OIDC at all — isolates the highest-regression-risk part from the genuinely new part.
- [OIDC is genuinely new integration surface with real security stakes (token validation, redirect URIs, state/nonce handling)] → Use a well-established OIDC client library rather than hand-rolling protocol handling; scope this change's acceptance to "a user can complete OIDC login and reach an authenticated session mapped to a stable Principal," not a full enterprise-SSO feature set (session refresh via OIDC token refresh, SLO, etc. are explicitly out of scope unless required later).
- [Two providers selected simultaneously (local + OIDC) means the login page must present a choice, which doesn't exist today] → `LoginPage.tsx` needs a "sign in with OIDC" affordance alongside the existing username/password form when more than one provider is selected; this is a small, additive UI change, not a redesign of the login flow.
- [Built-in RBAC evaluator must be an exact behavioral match for today's ownership rule, or every ownership-based-edit scenario across every kind regresses at once] → Port the check as a literal extraction (same code, moved), verified against `catalog-auth`'s existing scenarios plus `extract-c4-plugin`'s `atlas.c4.diagram.read` scenario, before anything else in this change proceeds.

## Migration Plan

1. Extract the built-in RBAC `PolicyEvaluator` from today's inline ownership check (literal move); repoint `atlas.c4.diagram.read`'s check (currently the change-7 stand-in) at it; verify `catalog-auth` and `catalog-c4-diagrams`-adjacent permission scenarios.
2. Add the `AuthenticationProvider` extension point and `atlas.auth.local`, wrapping today's allauth-headless flow with no behavior change; verify every `catalog-auth` scenario.
3. Add `ExternalIdentityLink` and `atlas.auth.oidc`; implement OIDC login → claims mapping → `Principal` resolution → session establishment.
4. Add the claims-to-Group mapping step; add the login-page provider choice UI when multiple providers are selected.
5. Verify: local-only deployment behaves identically to today; local+OIDC deployment allows login via either; OIDC-default deployment still allows local break-glass login.
6. Rollback: step 1 is a pure refactor, safe to revert alone; steps 2-4 are additive (new provider machinery) layered on an unchanged local flow, so OIDC specifically can be disabled/reverted without affecting local auth.

## Resolved

- **Is `atlas.auth.local` mandatory?**: no — not hard-required at the composition-validator level, unlike `atlas.standard-catalog`. A pure-OIDC-with-no-local-fallback deployment is a legitimate operator choice (e.g. an org that centralizes all access through its IdP and treats break-glass access as an infrastructure-level, not Atlas-level, concern). Document the break-glass recommendation prominently in deployment docs instead of enforcing it in code.
