## Context

Atlas uses the stock Django User with related models for account extensions. An AccountAccess side-car fits that model. Current mutation paths are not limited to RBACPolicyEvaluator and EntityWritePermission.check_create: TagWritePermission and CatalogHomeSettingsWritePermission check superuser directly, Django admin has its own permissions/actions, and plugins can invoke services or schedule work. These paths must participate in the same read-only restriction.

The frontend already uses `/api/me/` for account-level access information. `isReadOnly` extends that representation; it is a presentation signal, not session-frozen authorization state. The separate YAML-managed entity concept remains unchanged.

## Goals / Non-Goals

**Goals:** give operators a reliable account-wide restriction on user-initiated writes, preserve ordinary read permissions, apply changes to live sessions, and enforce the restriction regardless of provider, owner membership, grants, superuser status, or selected evaluator.

**Non-Goals:** per-Group reader roles, a new identity provider, a replacement User model, immediate cancellation of already committed work, or sandboxing hostile installed plugins. No public self-service flag mutation is added. Reading one's own flag is supported.

## Decisions

### 1. Read-only is a mandatory Core restriction

The Authorization Service presents a Core-guarded facade around the selected PolicyEvaluator. Core and `atlas_plugin_api.get_policy_evaluator()` consumers receive this facade, never the raw selected implementation. For a read-only Principal, Core denies a write or unknown permission before delegating. Ordinary read decisions and non-read-only behavior still go to the selected evaluator. The built-in evaluator also observes the restriction if it has supported direct call sites; those sites should migrate to the facade.

Use one shared account-state predicate and write guard for entry points outside evaluator delegation: entity creation without a resource, direct superuser guards, admin, and job dispatch. Preserve the existing `PolicyEvaluator.check(principal, permission, resource)` arguments. Do not change `is_group_member` to return false for read-only accounts; memberships and stored Purge Grants remain intact. A helper that answers whether purge is authorized must apply the same guard before privilege shortcuts.

**Alternative:** change only RBACPolicyEvaluator. Rejected because another evaluator and existing direct/admin guards could bypass it.

### 2. Permission effects are explicit and conservative

Extend permission registration with optional `effect: read | write`. For compatibility, registered ids ending in `.read` default to read; all other registered ids default to write, including `.execute`, `.sync`, `.adopt`, and unfamiliar suffixes. Explicit read declarations require a side-effect-free user operation and contract coverage. Unknown/unregistered ids are denied for read-only callers even when a selected evaluator would allow them. Validate conflicting or invalid effect declarations at registration/composition. Existing registration calls remain valid and this change does not otherwise expand permissions for normal accounts.

Permission naming does not prove behavior. Inventory actual routes, services and actions so an operation that mutates state cannot be mislabeled read. Core guards apply before persistence, remote effects, and enqueueing. A read-only request must not leave partial changes or queued work.

**Clarification (task 3.1, recorded during implementation):** Core registers none of its own per-Entity-Kind permission ids (`<kind>.read`, `.edit`, `.create`, `.delete`, `.purge`) through `register_permission` — only plugins register ids today. Applying "unregistered is write" literally against `PermissionRegistry` would therefore deny every core entity *read* too, not just writes. The guard classifies these five suffixes structurally, independent of whether the id was ever registered (`.read` → read; `.edit`/`.create`/`.delete`/`.purge` → write); `PermissionRegistry`'s effect metadata is consulted only for a permission id that ends in none of the five — e.g. a plugin-declared `.execute`/`.sync`/custom-named id. This is what `atlas_plugin_api.permissions.classify_permission_effect()` implements, and does not change the compatible-default behavior described above for anything ending in `.read`.

### 3. AccountAccess stores operator-managed state

Use an O2O `AccountAccess(account, read_only=False, updated_at)` related to `settings.AUTH_USER_MODEL`. A missing row means false for compatibility; database/query failures do not mean a missing row and fail authorization closed. Do not store this flag as an authoritative session claim or process-wide cached value.

A custom UserAdmin inline exposes the flag to a non-read-only operator with the explicit AccountAccess change permission and authority over the target User. Account creation and setting its read-only flag commit together before the new account can authenticate. Creating, changing, or deleting AccountAccess must pass equivalent authorization and write an audit event containing operator, target, old/new values, and timestamp in the same transaction. Disable inline deletion as the normal UI; set false explicitly. Any supported deletion path, including bulk actions, must be treated as removing the restriction and audited.

A read-only staff/superuser cannot change users, flags, grants, memberships, or any other admin-managed state, including unflagging itself. Read-only admin viewing follows existing view permissions. Deny admin add/change/delete, inlines, bulk actions, and custom mutation views server-side; hiding widgets is insufficient. A non-read-only authorized operator may remove a flag. An authenticated web session cannot invoke infrastructure recovery.

Provide an operator-only management command for emergency recovery with explicit target, reason, safe dry-run output, and audit. This is an infrastructure exception to normal admin-only flag management, not a public API or bypass for a read-only session. Preserve staff/superuser/login policies; read-only alone grants no administrative access.

### 4. Define the mutation boundary by intent

Maintain an inventory of registered mutation endpoints, admin actions, service entry points and user-triggered jobs with their guard and tests. Cover entity create/edit/remove/revive/purge/adopt, relationship/dependency changes, tag colors, catalog home/configuration, memberships/access controls, and plugin mutations present in the selected distribution.

User-triggered jobs persist the initiating Principal and recheck current authorization before executing mutations. A request already denied read-only must enqueue nothing; a queued job whose initiator becomes read-only must perform no later mutation. Independently scheduled system ingestion remains a service operation with its existing trust boundary. A user request cannot choose an ingestion/system identity or a `source` argument to escape the guard.

**Clarification (task 4.2, recorded during implementation):** this codebase has no user-triggered background job/enqueueing mechanism today. The only background-job runtime present (`django-apscheduler`, `atlas_plugin_ingestion`) runs `DISCOVERY_JOB_ID`/`SPEC_REFRESH_JOB_ID` on a schedule, not from a user request — it is exactly the "independently scheduled system ingestion" this decision already carves out. What looks like a deferred "sync" (`ApiDetails.spec_resolved_at`/`endpoints_synced_at`/`operations_synced_at`) is fetched and written synchronously, inline within the same request that `EntityWritePermission`/`CoreGuardedEvaluator` already authorize before `EntityService.create`/`update` calls the kind handler (task 3.x) — there is no separate later point in time, and therefore no separate recheck, needed for it. This requirement has no additional call site to guard in the current distribution; it constrains a future user-triggered job dispatcher (e.g. one introduced by `productionize-authentication-providers` or a later change) to call `is_account_read_only` at execution time, not only at enqueue time, rather than describing code added by this change.

Allowed service changes include login/logout, session maintenance, security audit and Core-controlled identity/profile/group provisioning. Explicit existing credential recovery/change flows may operate under their dedicated security policy and cannot change AccountAccess. These exceptions do not expose general account/profile/catalog editing to read-only users. Do not block all POST requests: some establish sessions or perform read-only queries. Conversely, a mutating GET is not exempt.

### 5. Live sessions use current access state

Every new request checks the persisted flag at its authorization boundary; any cache is limited to that request. After an operator's flag update commits, later authorization checks in new requests and queued jobs use the new value across all workers and sessions. Previously committed work is not undone; a write already authorized before the change is not promised to be cancelled. Removing the flag restores ordinary evaluator decisions, not unconditional writes.

`/api/me/` returns Python `is_read_only` serialized as `isReadOnly` alongside `isAdmin`, from current persisted state, without granting mutation rights. Frontend state refreshes on session initialization/login, focus or visibility return, before entering write routes, and after a write-denied response. Errors/loading must not render write controls as authorized. No real-time push is required; backend enforcement is immediate at the defined authorization boundary even if a visible form is stale.

### 6. UI applies the restriction across shared and custom pages

Keep `read_only`/`isReadOnly`; distinguish account restrictions from YAML-managed entity provenance in user-facing text. Use a shared write guard for mutation routes and explicit gating for in-place controls. Inventory route ids rather than assuming the existing ten create/edit routes cover the application. Include custom Flow pages, relationship editors, tags/settings and any installed plugin mutation controls. The Flows Add action is covered alongside row/detail actions.

Mixed read/write pages remain viewable but hide mutation controls. A pure mutation route redirects to a safe read page and does not flash a form while access state is loading. Read/export/navigation actions remain available under normal permissions, including those in menus that also contain write actions. `/api/me/` reading is intentionally allowed; self-service flag mutation is not.

### 7. Authentication and membership changes preserve the restriction

Providers, verified claims, external groups, profile allowlists, linking and automatic provisioning cannot set, clear, delete, or overwrite AccountAccess. All login methods for one Principal share the same flag. Manual or provider-managed membership grants and Purge Grants cannot override it. Admin break-glass allows authentication only and does not bypass read-only authorization.

For an external account that must be read-only before its first login: an operator creates the Principal with the flag atomically, then uses the authentication change's exact identity-link administration and `preprovisioned` mode before granting access. Automatic creation followed by later flagging is not equivalent and leaves an unrestricted window. No mapping from provider claims to this flag is added.

### 8. Implementation order and handoff

Implement and archive `add-readonly-role` first, then rebase/refresh `productionize-authentication-providers` against the updated code and main specs. This change does not depend on GroupMembershipGrant, source namespaces, or the new authentication gateway. It uses the current membership interface with independent denial before membership evaluation.

The authentication implementation must retain the guard and `isReadOnly` while refactoring authorization.py, api/permissions.py, admin.py, auth.ts, SessionContext and migration dependencies. Its integration acceptance matrix covers manual/provider grants, superuser/Purge Grant, repeat external login, linking, membership migration, and break-glass. Run applicable current-provider cases now; run future grant/gateway scenarios once those features exist. No authentication feature is silently implemented as part of this change.

#### Authentication integration handoff (task 9.4)

The later authentication implementation overlaps these current seams and must preserve their
contracts rather than replace them:

| Seam | Current dependency to retain | Combined acceptance when the later change implements it |
| --- | --- | --- |
| `core/backend/server/apps/catalog/authorization.py` | `is_account_read_only` reads current persisted state and `CoreGuardedEvaluator` denies writes before evaluator privilege shortcuts. | Effective membership grants replace only membership lookup; permissive evaluators, superusers, Purge Grants and new provider grants still cannot bypass the facade. |
| `core/backend/server/apps/catalog/api/permissions.py` | Resource-less create and direct tag/home-setting privilege paths call the shared predicate; entity writes use the guarded evaluator. | Gateway and provider metadata cannot select a service identity or skip these guards; any new user-triggered dispatcher checks at enqueue and execution. |
| `core/backend/server/apps/catalog/admin.py` | The custom `UserAdmin` attaches `AccountAccessInline`, global admin mutation guards, and transactional audit behavior. | Extend this class when adding identity/link/grant administration; do not replace the inline, allow self-unrestriction, or let break-glass exempt writes. |
| `core/frontend/src/lib/auth.ts` | Every established session combines allauth state with `/api/me/` and keeps `isReadOnly` separate from `isAdmin`. | The Atlas gateway and compatibility routes fetch current `isReadOnly` after local login and every external callback; no provider/session claim becomes authoritative. |
| `core/frontend/src/lib/SessionContext.tsx` | Initialization, focus/visibility, mutation-route, and write-denial refreshes fail safe while state is unknown or errored. | New provider choice/callback/session plumbing retains every refresh trigger and never flashes mutation UI before access state resolves. |
| `core/backend/server/apps/catalog/migrations/0025_accountaccess.py` | Additive side-car and audit models depend on the current catalog migration chain and `AUTH_USER_MODEL`. | Provider/source/link and membership-grant migrations depend forward from the rebased chain; forward and reverse migrations preserve every row and never recreate it with `read_only=False`. |

Current acceptance cases run in this change: local and repeated external identity resolution
preserve the flag; current OIDC group mapping cannot override it; existing-session flag changes,
direct write guards, admin bypass attempts, and `/api/me/` refresh semantics remain covered. The
later change owns cases that require features not present here: another linked provider,
source-aware manual/provider grants and their migration, the Atlas authentication gateway,
allowlisted admin break-glass, exact preprovisioned linking, and any new user-triggered jobs.

## Risks / Trade-offs

- **Uninventoried mutation bypasses the evaluator** → Release requires a route/action/service inventory and direct-request negative tests, not only evaluator unit tests.
- **Plugin mislabels a write as read** → Validate metadata and test operation effects. Installed plugins are trusted server code; the contract cannot contain malicious code.
- **Operator locks out all writable administrators** → Document the audited infrastructure recovery command; do not let a read-only admin clear its own restriction.
- **UI or long-running work sees old state** → Refresh presentation state, check backend state per request/job, and document the boundary for already-authorized operations.
- **Authentication changes overlap code and migrations** → Land this change first and carry the regression matrix into the second change.
- **Rollback restores write access** → Export affected accounts and block/deactivate them or retain equivalent guards before running a version that ignores AccountAccess. Never describe dropping the table as a harmless rollback after flags are assigned.

## Migration Plan

1. Inventory mutation entry points and register permission effects with compatible defaults.
2. Add AccountAccess and audited operator management/recovery; keep existing accounts false when no row exists.
3. Bind the Core-guarded evaluator and guard independent mutation/admin/job paths before exposing flag assignment.
4. Publish current `/api/me/` state and frontend refresh/route/control gating.
5. Pass bypass, live-session, alternate evaluator and normal-account regression tests; document account issuance and recovery.
6. Archive this change before applying the authentication provider refactor, whose combined tests preserve these guarantees.

Schema changes are additive. Once accounts are flagged, rollback is security-sensitive as described above.

## Open Questions

No unresolved product decision blocks implementation. Read-only overrides superuser; the storage is a boolean; the public presentation field is `isReadOnly`. The concrete mutation inventory and audit integration are implementation prerequisites tracked in tasks, not exceptions to the requirements.
