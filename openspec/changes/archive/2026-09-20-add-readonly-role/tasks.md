## 1. Inventory and compatibility

- [x] 1.1 Inventory all user-mutation routes, admin actions/inlines/custom views, service entry points, and user-triggered jobs; record each guard and negative test, including tags, home settings, relationships, adopt, and installed plugin actions.
- [x] 1.2 Inspect permission registration and evaluator binding; identify every supported raw-evaluator/direct privilege call site and define the guarded facade without changing PolicyEvaluator.check arguments.
- [x] 1.3 Record implementation order: land and archive this change first; then rebase productionize-authentication-providers and retain the regression contract from design Decision 8.

## 2. Account state and audited operator management

- [x] 2.1 Add AccountAccess O2O to AUTH_USER_MODEL with read_only=False and updated_at; export it and generate an additive migration.
- [x] 2.2 Implement one shared current-state predicate: missing row is false, query errors fail closed, and no authoritative session/process-wide cache is used.
- [x] 2.3 Add the UserAdmin inline with explicit AccountAccess permission and target-user permission checks for non-read-only operators; commit creation of a flagged User and its AccountAccess atomically.
- [x] 2.4 Audit flag creation/update/removal with operator, target, old/new values and timestamp in the same transaction; disable normal inline deletion and protect any other supported deletion/bulk path equivalently.
- [x] 2.5 Add and document an infrastructure-only recovery command with exact target, reason, safe dry run and audit; expose no equivalent self-service web operation.

## 3. Core authorization and plugin contracts

- [x] 3.1 Add optional read/write effect metadata to permission registration, default registered .read ids to read and all other ids to write; validate invalid/conflicting declarations while preserving existing calls.
- [x] 3.2 Bind a Core-guarded facade around the selected evaluator for both Core and public Plugin API lookup; deny read-only write/unknown permissions before delegation and privilege shortcuts.
- [x] 3.3 Apply the shared guard to resource-less EntityWritePermission.check_create and supported direct purge-authorization helpers; preserve actual membership/grant state.
- [x] 3.4 Guard direct superuser mutation paths such as TagWritePermission and CatalogHomeSettingsWritePermission and every additional mutation found in the inventory before side effects.
- [x] 3.5 Document and test plugin effect semantics and guarded public access, including .execute/.sync and explicitly read nonstandard queries; do not claim malicious-plugin sandboxing.
- [x] 3.6 Preserve normal-account evaluator behavior and ordinary read permissions, including custom selected evaluators.

## 4. Admin and deferred mutations

- [x] 4.1 Enforce read-only server-side across Django admin add/change/delete, inline writes, mutating bulk actions and custom mutation views; preserve authorized viewing and prevent self-unrestriction.
- [x] 4.2 Guard user-triggered mutation enqueueing, retain initiating Principal on jobs and reauthorize before job mutations; prevent caller-controlled system/ingestion identity bypasses.
- [x] 4.3 Keep independently scheduled service ingestion, login/logout, sessions, audit, Core provisioning and explicitly supported credential security flows under their existing security policies; ensure none can mutate AccountAccess as a user bypass.

## 5. Current-user API and frontend state

- [x] 5.1 Add is_read_only to MeOut/MeController serialized as isReadOnly from current account state; leave self-service mutation unavailable.
- [x] 5.2 Extend SessionState and all state literals/reset paths with isReadOnly; retain isAdmin as a separate fact.
- [x] 5.3 Refresh access state on initialization/login, focus or visibility return, before mutation-route entry, and after write-denied responses; do not render write forms while state is unknown or failed.
- [x] 5.4 Provide safe stale-form handling after a 403 without reporting success or relying on UI for security.

## 6. Frontend route and control coverage

- [x] 6.1 Implement shared WriteProtected guarding and enumerate actual mutation routes for all installed kinds/plugins rather than stopping at the original ten create/edit route ids.
- [x] 6.2 Gate EntityListPage Add and entity detail Edit/Remove/Revive/Purge controls, including row write actions, while retaining permitted read/export/navigation entries.
- [x] 6.3 Gate Flow Add, detail and row write actions plus create/edit routes and test direct Flow API denial.
- [x] 6.4 Gate relationship editors, settings/tag/home saves and plugin mutation triggers from the inventory; retain read content on mixed pages and apply restrictions even when isAdmin is true.
- [x] 6.5 Keep account-read-only messaging distinct from YAML-managed entity provenance and preserve existing normal-account affordances.

## 7. Backend regression and bypass tests

- [x] 7.1 Test read-only owner members against create/edit/remove/revive/purge/adopt and relationship mutations; assert 403 and no partial state or side effects.
- [x] 7.2 Test read-only superusers and Purge Grant holders, including tags, settings and direct privilege guards, while confirming membership/grants remain stored unchanged.
- [x] 7.3 Test a permissive alternate evaluator, unknown permission, .execute/.sync write defaults, explicit nonstandard read effect and public plugin evaluator lookup.
- [x] 7.4 Test crafted admin inline POST, AccountAccess deletion, bulk actions and custom admin mutations; verify no self-unrestriction and normal authorized admin viewing.
- [x] 7.5 Test flag-change permission/audit/atomic creation, rollback on audit failure, recovery command and missing-row versus database-error semantics.
- [x] 7.6 Test an already logged-in user across multiple sessions/workers after flag on/off: next authorization reflects state and removal restores ordinary permission evaluation only.
- [x] 7.7 Test denied enqueue creates no job, queued job rechecks changed access, and caller-selected system/source metadata cannot bypass the restriction.
- [x] 7.8 Test successful read/login/logout and service maintenance, ensuring no new read privileges or AccountAccess changes are introduced.
- [x] 7.9 Test /api/me/ true/false output and current local/available external login preservation of an existing flag.

## 8. Frontend and end-to-end tests

- [x] 8.1 Test WriteProtected loading/error/redirect/normal behavior and that mutation forms never flash while state is unresolved.
- [x] 8.2 Test shared list/detail/row, Flow Add/detail/row, relationship and settings controls for read-only and read-only admin sessions; retain allowed read actions.
- [x] 8.3 Test flag change while a form is open, focus refresh, and refresh after rejected submission; direct HTTP writes must remain denied with stale frontend state.
- [x] 8.4 Run a representative browser journey: operator creates flagged account, user browses, direct write fails, another operator clears flag, and only ordinarily authorized writes resume.

## 9. Documentation, rollout and authentication handoff

- [x] 9.1 Document operator flag management, self-status visibility, audit, infrastructure recovery, existing-session effect, permitted service operations and the in-flight authorization boundary.
- [x] 9.2 Document external read-only issuance before first access using a flagged pre-created Principal and future identity-link/preprovisioned workflow; warn that automatic creation then later flagging leaves a writable window.
- [x] 9.3 Record authentication integration acceptance cases: repeated provider login/linking preserves AccountAccess; manual/provider grant migration cannot override it; admin break-glass remains subject to it; new auth/session plumbing preserves isReadOnly.
- [x] 9.4 Identify overlapping authorization.py, api/permissions.py, admin.py, auth.ts, SessionContext and migration dependencies for the later authentication implementation; run current cases now and future grant/gateway cases when that change implements them.
- [x] 9.5 Document rollback after flags are assigned as security-sensitive: preserve equivalent guards or block affected accounts before deploying a version that ignores AccountAccess.
- [x] 9.6 Run appropriate backend/frontend/plugin contract and integration suites, typing/lint/migration checks, and strict OpenSpec validation; verify the mutation inventory has no uncovered entries before declaring completion.
