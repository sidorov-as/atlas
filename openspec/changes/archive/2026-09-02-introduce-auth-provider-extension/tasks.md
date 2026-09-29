## 1. Extract the policy evaluator

- [x] 1.1 Define `PolicyEvaluator` Protocol (`check(principal, permission, resource) -> bool`) and a `PolicyEvaluator` singleton extension point.
- [x] 1.2 Extract the built-in RBAC evaluator from today's inline ownership check (literal move, no behavior change).
- [x] 1.3 Repoint `atlas.c4.diagram.read`'s check (the `extract-c4-plugin` stand-in) at the real evaluator.
- [x] 1.4 Verify `catalog-auth` ownership scenarios and the C4 permission scenario.

## 2. Authentication provider extension point and local provider

- [x] 2.1 Define the `AuthenticationProvider` keyed extension point and `Principal`/`ExternalIdentity` mapping contract.
- [x] 2.2 Create `atlas.auth.local` wrapping today's allauth-headless flow with no behavior change.
- [x] 2.3 Verify every `catalog-auth` scenario against the provider-mediated flow.

## 3. OIDC provider

- [x] 3.1 Add `ExternalIdentityLink` (`user`, `provider_id`, `external_subject`).
- [x] 3.2 Implement `atlas.auth.oidc` using an established OIDC client library: login redirect, callback, token/claims validation, `Principal` resolution.
- [x] 3.3 Implement the claims-to-Group mapping step, run after successful authentication, separate from `PolicyEvaluator.check`.

## 4. Multi-provider UX and verification

- [x] 4.1 Add a provider-choice affordance to `LoginPage.tsx` when more than one provider is selected.
- [x] 4.2 Verify: local-only deployment behaves identically to today.
- [x] 4.3 Verify: local+OIDC deployment allows login via either, and OIDC claims never bypass `PolicyEvaluator` checks.
- [x] 4.4 Verify: OIDC-default deployment still allows local break-glass login when `atlas.auth.local` is also selected.
