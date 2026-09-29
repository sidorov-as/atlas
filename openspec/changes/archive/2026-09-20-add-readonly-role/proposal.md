## Why

Operators need accounts that can browse Atlas without changing catalog data, configuration, access controls, or starting mutations, even when those accounts belong to owner Groups or hold staff, superuser, or Purge Grant privileges. Current write checks are spread across the policy evaluator, entity creation, direct superuser guards, Django admin, and plugin operations; changing only the built-in evaluator would leave bypasses.

## What Changes

- Add a Principal-level `AccountAccess.read_only` boolean, defaulting to false when no row exists, without replacing `AUTH_USER_MODEL`.
- Enforce read-only through a mandatory Core authorization guard before the selected evaluator and before independent mutation entry points. Membership and grants retain their meaning; read-only restricts use of write privileges.
- Classify registered permissions as read or write. Existing registered `.read` permissions retain read semantics; all other permissions default to write unless explicitly declared read and reviewed as side-effect-free. Unknown permissions fail closed for read-only callers.
- Inventory and guard entity CRUD/lifecycle, relationships, tags, settings, plugin actions, Django admin actions/inlines, and user-triggered background mutations before side effects or enqueueing.
- Allow only authorized non-read-only operators to change the flag through Django admin, with transactional audit. Prevent self-unrestriction and deletion of the side-car row as a bypass; provide an audited infrastructure recovery procedure for operator lockout.
- Apply flag changes at the next authorization check in every existing session without requiring login again. `/api/me/` exposes `isReadOnly` for the caller; clients can read but cannot mutate this state.
- Hide write controls and guard mutation routes across the core shell, custom plugin pages, and administrative settings while keeping read-only navigation available. Refresh frontend access state without trusting it for enforcement.
- Preserve login/logout, session maintenance, audit, and explicitly Core-owned authentication provisioning. Do not implement read-only as a blanket HTTP-method or database-write prohibition.
- Implement this change before `productionize-authentication-providers`; retain the restriction across provider login, identity linking, membership migration, session refactoring, and admin break-glass.

**Compatibility:** existing accounts remain unrestricted unless explicitly flagged. Existing registered read permissions retain behavior; new metadata supports nonstandard permission names. Plugin authors must route mutations through the guarded authorization surface. Removing this feature after flags have been assigned would restore write privileges and is a security-sensitive rollback.

## Capabilities

### New Capabilities

None; this change extends existing account, authorization, and UI capabilities.

### Modified Capabilities

- `catalog-auth`: account-wide read-only semantics, admin management/audit, existing-session freshness, mutation coverage, service-operation exceptions, and provider independence.
- `policy-evaluator-extension`: mandatory Core restriction before the selected evaluator, permission-effect classification, and plugin/service conformance.
- `catalog-web-ui`: access-state exposure/refresh, write-control hiding, and route guards across shared and administrative UI.
- `flow-management`: the same restrictions on bespoke Flow controls, routes, and backend mutations.

## Impact

- Backend: AccountAccess model/migration, guarded evaluator binding and direct mutation guards, UserAdmin/AdminSite integration, audit, `/api/me/`, and user-triggered job authorization.
- Plugin API: permission-effect registration metadata and a documented Core-guarded evaluator surface; no provider-specific role system or change to `PolicyEvaluator.check` arguments.
- Frontend: session access-state refresh, write route guards, shared controls, plugin controls, and settings forms.
- Tests/docs: endpoint/action inventory, alternate evaluator and admin bypass tests, live-session updates, operator recovery, and authentication integration handoff.
