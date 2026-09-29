# add-readonly-role — Mutation & Authorization Inventory (tasks 1.1 / 1.2)

Produced during `/opsx:apply add-readonly-role`, task group 1 ("Inventory and
compatibility"). This is a research artifact, not code — later tasks (2.x–9.x)
should treat it as the checklist for "did we guard everything."

## 1.3 Implementation order (recorded, not re-decided)

Per design.md Decision 8 and its Migration Plan step 6: implement and archive
`add-readonly-role` in full — including this inventory, the guarded facade,
`AccountAccess`, all frontend gating, and the backend/frontend regression
suites (tasks 2–9) — **before** rebasing `productionize-authentication-providers`
against the resulting code. That later change must carry forward the same
regression contract (manual/provider grants, superuser/Purge Grant, repeat
external login, linking, membership migration, break-glass — design.md
Decision 8's acceptance matrix) rather than re-deriving it, and must not
silently reintroduce a write path that skips the read-only guard while
refactoring `authorization.py`/`api/permissions.py`/`admin.py`/`auth.ts`/
`SessionContext`. No action needed here beyond this record — design.md already
states the order; this section exists so the sequencing lives in the task-1
checklist too, not only in a decision doc some later reader might skip.

## 1.1 Mutation surface inventory

Legend for **Guard** column: `EntityWritePermission` = goes through the shared
ownership/ policy-evaluator gate; `is_superuser` (direct) = bypasses the
evaluator entirely; `evaluator` (plugin) = calls
`get_policy_evaluator().check(...)` directly; `Django perm` = Django's
built-in `auth.<app>.<action>_<model>` permission via `ModelAdmin`;
**none** = no permission check at all today.

### A. Core entity CRUD/lifecycle (System, Component, Resource, Group, Actor, API)

All create/update/remove/revive/delete/purge for every kind funnels through
one place: `EntityService` at
`core/backend/server/apps/catalog/services/entity_service.py`.

| Operation | Entry point | Guard | Negative test |
|---|---|---|---|
| create | `EntityService.create` (`entity_service.py:182-232`) | `EntityWritePermission.check_create` (`api/permissions.py:44-46`) — **direct call to `is_group_member`, bypasses `policy_evaluator` entirely** (`entity_service.py:216`) | `core/backend/server/apps/catalog/tests/` ownership tests exist; no read-only case (flag doesn't exist yet) |
| update | `EntityService.update` (`entity_service.py:234-274`) | `EntityWritePermission.check_write` → `policy_evaluator.check(f'{kind}.edit')` (`api/permissions.py:48-53`) | same |
| remove | `EntityService.remove` (`entity_service.py:276-304`) | `EntityWritePermission.check_write` | same |
| revive | `EntityService.revive` (`entity_service.py:306-328`) | `EntityWritePermission.check_write` | same |
| delete | `EntityService.delete` (`entity_service.py:330-344`) | `EntityWritePermission.check_write` | same |
| purge | `EntityService.purge` (`entity_service.py:346-397`) | `EntityWritePermission.check_purge` → `policy_evaluator.check(f'{kind}.purge')` → `has_purge_grant` (`authorization.py:46-61`) | same |

Note: `source='yaml'` skips `EntityWritePermission` entirely for
create/update/remove/revive (ingestion's own re-claim, `entity_service.py:215,251,291,315`)
— this is a service-identity path, not a user-facing one; confirm no user
request can set `source` (see §1.1.F).

Per-kind HTTP controllers calling into `EntityService` (all inherit the guard
above transitively — no separate authorization logic in the controller layer):

- Standard-catalog (`plugins/standard-catalog/backend/atlas_plugin_standard_catalog/api/views.py`): `SystemListController.post:150`, `SystemDetailController.patch:168`, `SystemAdoptController.post:229`, `SystemRemoveController.post:241`, `SystemReviveController.post:251`, `SystemPurgeController.post:261`; same pattern repeated for Component (`:346,364,399,411,421,431`) and Resource (`:501,519,554,566,576,586`). Group/Actor have list/detail/relations controllers only — no `.new`/`.edit` HTTP routes; they're created/edited exclusively via Django admin (`admin.py`, see §1.1.D).
- APIs plugin (`plugins/apis/backend/atlas_plugin_apis/api/views.py`): `ApiListController.post:199`, `ApiDetailController.patch:217`, `ApiAdoptController.post:252`, `ApiRemoveController.post:264`, `ApiReviveController.post:274`, `ApiPurgeController.post:284`, plus endpoint/operation purge-only controllers `ApiEndpointPurgeController.post:376`, `ApiOperationPurgeController.post:539` (endpoints/operations are otherwise ingestion-owned, no create/edit route).
- Flows plugin (`plugins/flows/backend/atlas_plugin_flows/api/views.py`): `FlowListController.post:118-119`, `FlowDetailController.patch:133,138`, `FlowDetailController.delete:145,148` — **Flow does not use `EntityService`/`CatalogEntity`**; it's a bespoke model. All three call `check_flow_write_permission(user, system)` (`atlas_plugin_flows/permissions.py:21-26`) before mutating, which does `get_policy_evaluator().check(user, FLOW_EDIT_PERMISSION, system)` — checked against the *owning System's* group membership. No adopt/remove/revive/purge lifecycle for Flow (plain create/edit/delete only). Verified by reading `views.py:118-148` directly.

### B. Core direct-mutation endpoints (no `EntityService`, no `CatalogEntity` lifecycle)

`core/backend/server/apps/catalog/api/views.py`:

| Endpoint | Guard | Negative test |
|---|---|---|
| `ArchitectureRelationshipListController.post` (:160) | `EntityWritePermission.check_write(source)` via `_manual_relationship_source` (:138,164) | unknown — check `tests/` |
| `ArchitectureRelationshipDetailController.patch` (:190) / `.delete` (:211) | `_check_relationship_write` → `EntityWritePermission.check_write` (:121-139) | unknown |
| `TagDetailController.patch` (:245) | `TagWritePermission.check_write` — **direct `request.user.is_superuser` check, `api/permissions.py:80-83`, bypasses `policy_evaluator` and the whole read/write-effect model entirely** | unknown |
| `CatalogHomeSettingsController.patch` (:266) | `CatalogHomeSettingsWritePermission.check_write` — **same direct `is_superuser` pattern**, `api/permissions.py:94-97` | unknown |

`MeController.get` (:71-72) is read-only (`/api/me/`) — the endpoint task 5.1
extends with `isReadOnly`.

### C. Plugin relationship/dependency mutation endpoints

`plugins/apis/backend/atlas_plugin_apis/api/views.py` — these already route
through the guarded-evaluator pattern via small permission helper functions in
`plugins/apis/backend/atlas_plugin_apis/permissions.py:45` (`get_policy_evaluator().check(...)`):

| Endpoint | Guard |
|---|---|
| `EndpointServicesController.post` (:713) | `check_endpoint_dependency_create_permission` → `ENDPOINT_DEPENDENCY_CREATE_PERMISSION` |
| `EndpointServiceController.delete` (:749) | `check_endpoint_dependency_delete_permission` → `ENDPOINT_DEPENDENCY_DELETE_PERMISSION` |
| `OperationServicesController.post` (:872) | `check_operation_dependency_create_permission` (pattern matches endpoint sibling) |
| `OperationServiceController.delete` (:913) | `check_operation_dependency_delete_permission` |

These are the model for what the guarded facade needs to sit behind — good
because they already go through `get_policy_evaluator()`, not a raw
`is_superuser` check.

### D. Unguarded mutation surface found

**`plugins/database-schema/backend/atlas_plugin_database_schema/api/views.py`,
`DatabaseSchemaController.post` (:111) and `.patch` (:121)** — only
`auth = (SessionAuth(),)`. No `EntityWritePermission`, no `policy_evaluator`,
no ownership check of any kind: **any authenticated user can create/edit the
Database Schema facet on any Resource today**, independent of read-only. This
is a pre-existing gap unrelated to this change's flag, but it must be closed
as part of task 3.4 ("every additional mutation found in the inventory")
since it currently has zero write guard for *anyone* to hook a read-only
check onto — needs an explicit `EntityWritePermission.check_write`-style call
added, not just a read-only wrapper.

### E. Django admin

No custom `ModelAdmin` actions, inlines, or bulk actions exist anywhere in the
repo today (`grep` for `@admin.action`/`actions = [` returned nothing) — every
registered admin is a plain `admin.ModelAdmin` relying on Django's default
add/change/delete permission checks (`auth.add_<model>` etc.) plus, for two
models, an extra manual gate:

- `core/backend/server/apps/catalog/admin.py`: `CatalogEntityAdmin` (:12), `ArchitectureRelationshipAdmin` (:20), `ExternalIdentityLinkAdmin` (:34), `PurgeGrantAdmin` (:42) — plain, no extra guard.
- `plugins/standard-catalog/backend/atlas_plugin_standard_catalog/admin.py`: `GroupDetailsAdmin` (:60), `ActorDetailsAdmin` (:113) — `save_model` routes through `get_entity_service().create/update(actor=request.user)` (:88-99, :146-155), so these **do** inherit `EntityWritePermission.check_create/check_write` (translated to Django's `PermissionDenied` via `_translate_permission_errors`, :34-40). This is the only admin write path already indirectly guarded by the evaluator.
- `plugins/flows/backend/atlas_plugin_flows/admin.py`: `FlowAdmin` — plain.
- `plugins/ingestion/backend/atlas_plugin_ingestion/admin.py`: `RegisteredRepositoryAdmin` (:7), `ConflictRecordAdmin` (:28) — plain; `RegisteredRepository` add/delete via admin is user-triggered (register/unregister a repo for ingestion) and currently has no read-only-aware guard beyond Django's own model permission.
- `plugins/apis/backend/atlas_plugin_apis/admin.py`: `ApiDetailsAdmin` (:7), `ApiEndpointAdmin` (:37), `ServiceEndpointUsageAdmin` (:67), `ApiOperationAdmin` (:75), `ServiceOperationUsageAdmin` (:114) — plain.

**No custom `AUTH_USER_MODEL`, no custom `UserAdmin`** — `django.contrib.auth`
is a plain installed app (`core/backend/server/settings/components/common.py:36`)
using its stock `User`/`UserAdmin` at `/admin/` (`urls.py:11`). Task 2.3's
"Add the UserAdmin inline" means **unregistering the default `UserAdmin` and
registering a custom one** (there is nothing to extend today), with an
`AccountAccess` inline.

Because every admin mutation today relies on Django's own permission model
(`is_staff`/`is_superuser`/per-model permissions) rather than
`policy_evaluator`, task 4.1's "deny admin add/change/delete... server-side"
cannot reuse `EntityWritePermission` for the *generic* admin case — it needs
its own shared predicate (design.md's "shared account-state predicate")
applied via a custom `ModelAdmin` mixin or `AdminSite` override so it covers
every registered model uniformly, not just the ones that happen to call
`EntityService`.

### F. Background / user-triggered jobs

No task-queue framework is used anywhere in the repo (`celery`, `django_rq`,
`apply_async`, `.delay(`, `enqueue` all return zero matches). Ingestion is the
only thing resembling asynchronous work, and it is **not** user-triggered:

- `plugins/ingestion/backend/atlas_plugin_ingestion/management/commands/ingest.py` — one-shot management command (operator/CI-run, not a web request).
- `plugins/ingestion/backend/atlas_plugin_ingestion/management/commands/runapscheduler.py` — APScheduler-driven periodic run, a standalone process. This is the "independently scheduled system ingestion" design.md §4/§7 calls out as staying under its own trust boundary.

**Conclusion: there is currently no user-triggered mutation-job entry point in
the codebase.** Tasks 4.2/7.7/7.3 ("Caller starts mutating work" /
"`.execute`/`.sync` write defaults") describe a *contract-level* concern for
future/plugin-declared permissions (nothing today registers a `.execute` or
`.sync` permission id — see §1.2) rather than an existing enqueue call site to
retrofit. Treat 4.2 as "guard the pattern when a plugin adds one" plus a
conformance test using a stub permission, not as a fix to existing code.

### G. Authentication / session / service-exempt paths (confirmed out of scope, per design.md §4)

- `_allauth/` (django-allauth headless), mounted at `core/backend/server/urls.py:12` — login/logout/session, Core-owned, untouched by this change.
- `core/backend/server/apps/catalog/authentication.py` — `AuthenticationProvider` extension point; provisions/links identities. Must be checked (task 9.3) to confirm no code path here can create or write `AccountAccess` — currently there's no such model, so trivially true today, but this file is the place a future auto-provisioning bypass would be introduced.
- `healthz/`, `healthz/plugins/` (`server/health.py`) — read-only, unauthenticated.

### H. Frontend mutation-affordance inventory (for task 6.x)

Route ids ending `.new`/`.edit` today — confirms design.md's "the original ten
create/edit route ids":

`atlas.apis.apis.new`, `atlas.apis.apis.edit` (`plugins/apis/frontend/src/routes.ts:12,14`);
`atlas.standard-catalog.systems.new/.edit` (`plugins/standard-catalog/frontend/src/routes.ts:19,21`);
`atlas.standard-catalog.components.new/.edit` (`:24,26`);
`atlas.standard-catalog.resources.new/.edit` (`:29,31`);
`atlas.flows.flows.new/.edit` (`plugins/flows/frontend/src/routes.ts:10,12`).

Teams (`Group`) has **no** `.new`/`.edit` route — created only via Django
admin — so no frontend gating is needed there beyond what §E covers server-side.

Shared write-affordance components (cover Systems/Components/Resources/APIs
list+detail pages, i.e. everything routed through `EntityListPage`/`EntityDetailShell`):

- `core/frontend/src/components/EntityListPage.tsx`: `onAdd` prop → "Add <Kind>" button (:22,140); `handleRemove` (:92-95) wired into row actions.
- `core/frontend/src/lib/entityRowActions.tsx`: `entityRowActions(onEdit, onRemove)` (:6) — builds the row context-menu's Edit/Remove entries; called from `EntityListPage.tsx:172` and each plugin's own list page (Flows: `FlowsListPage.tsx:97`).
- `core/frontend/src/components/EntityDetailShell.tsx`: Edit button (:207, gated on `isManual || canPurge`, :202), Remove (:210-213, `canRemove` :133), Revive (:215-218, `canRevive` :134), Purge (:220-223, `canPurge` :138).
- Flow-specific, **outside** the shared shell (flow-management spec explicitly calls this out): `plugins/flows/frontend/src/pages/FlowDetailPage.tsx` Edit button (:84) and Delete button (:88-89, `handleDelete` :45); `plugins/flows/frontend/src/pages/FlowsListPage.tsx` "Add Flow" (:80-81) and row actions (:97).
- Settings/config mutation surfaces: `core/frontend/src/pages/SettingsTagsPage.tsx` (tag color patch), `core/frontend/src/pages/SettingsHomePage.tsx` (catalog-home patch) — both currently gated only by `AdminProtected` (:`core/frontend/src/components/AdminProtected.tsx`), which checks `isAdmin`, not anything read-only-aware.

Existing guard pattern to imitate: `AdminProtected.tsx` (route-level
`<Navigate>` redirect based on `useSession()`), and
`core/frontend/src/lib/SessionContext.tsx` / `core/frontend/src/lib/auth.ts`'s
`SessionState` — currently `{ isAuthenticated, user, isAdmin }`, fetched once
on mount only (`SessionContext.tsx:20-32`, no focus/visibility/route-entry
refresh yet — this is exactly the gap task 5.3 must close). `isAdmin` itself
comes from `/api/me/` (`auth.ts:32-35`), the same endpoint task 5.1 extends.

## 1.2 Permission registration and evaluator binding

### Registration mechanism

`plugin-api/python/atlas_plugin_api/permissions.py`:
- `PermissionRegistry` (:62-83) tracks only a flat set of `permission_id → owner`, for **duplicate-id conflict detection**, not authorization. No effect/read-write metadata exists today.
- `register_permission(permission_id, owner=...)` (:89-96) — the only registration call.
- All call sites (plugin-declared ids only — **Core registers none of its own `<kind>.read/.edit/.create/.delete/.purge` ids anywhere**):
  - `plugins/apis/backend/atlas_plugin_apis/plugin.py:88-97` — `ENDPOINT_READ_PERMISSION`, `ENDPOINT_PURGE_PERMISSION`, `ENDPOINT_DEPENDENCY_READ_PERMISSION`, `ENDPOINT_DEPENDENCY_CREATE_PERMISSION`, `ENDPOINT_DEPENDENCY_DELETE_PERMISSION`, `OPERATION_READ_PERMISSION`, `OPERATION_PURGE_PERMISSION`, `OPERATION_DEPENDENCY_READ_PERMISSION`, `OPERATION_DEPENDENCY_CREATE_PERMISSION`, `OPERATION_DEPENDENCY_DELETE_PERMISSION`.
  - `plugins/c4/backend/atlas_plugin_c4/plugin.py:43` — `DIAGRAM_READ_PERMISSION`.
  - `plugins/flows/backend/atlas_plugin_flows/plugin.py:43-44` — `FLOW_READ_PERMISSION`, `FLOW_EDIT_PERMISSION`.
  - No currently-registered id ends in `.execute`, `.sync`, or `.adopt` — those suffixes are anticipated by the spec/design (`.adopt` is used as a *permission the RBAC evaluator checks via the `.edit` suffix internally* — `ApiAdoptController`/`SystemAdoptController` etc. call `policy_evaluator.check(f'{kind}.edit', ...)`, not a separate `.adopt`-suffixed id) but don't exist as registered ids yet.

**Design gap to resolve in task 3.1/3.2**: since Core never calls
`register_permission` for its own `<kind>.read/.edit/.create/.delete/.purge`
ids, a naive "unregistered ids are denied for read-only callers" rule would
break every core entity permission. The guarded facade must special-case the
five core CRUD suffixes (treat `.read` as read, `.edit`/`.create`/`.delete`/`.purge`
as write) independent of the `PermissionRegistry`, and only consult the
registry's new effect metadata for plugin-declared ids that don't match one of
those suffixes. This should be made an explicit decision recorded when task
3.1 is implemented (or folds back into design.md as a clarification) rather
than assumed.

### `PolicyEvaluator.check` — definition and every call site

Definition: `Protocol` in both `core/backend/server/apps/catalog/authorization.py:81-90`
and its structural twin `plugin-api/python/atlas_plugin_api/permissions.py:100-109`
(`runtime_checkable`). Concrete implementation: `RBACPolicyEvaluator.check`
(`authorization.py:93-118`). Binding: `bind_policy_evaluator(policy_evaluator)`
called once from `core/backend/server/apps/catalog/plugin.py:47`, during
`register_runtime()` (`:43-47`). Retrieval: `get_policy_evaluator()`
(`plugin-api/python/atlas_plugin_api/permissions.py:126-139`).

Call sites of `policy_evaluator.check(...)` / `get_policy_evaluator().check(...)`
(every one of these is where the guarded facade in task 3.2 must be
substituted in):

1. `core/backend/server/apps/catalog/api/permissions.py:52` — `EntityWritePermission.check_write` (`<kind>.edit`).
2. `core/backend/server/apps/catalog/api/permissions.py:59` — `EntityWritePermission.check_adopt` (`<kind>.edit`).
3. `core/backend/server/apps/catalog/api/permissions.py:68` — `EntityWritePermission.check_purge` (`<kind>.purge`).
4. `plugins/apis/backend/atlas_plugin_apis/permissions.py:45` — generic `check(user, permission, resource)` helper used by all five of that plugin's permission functions (endpoint/operation read, purge, dependency create/read/delete).
5. `plugins/c4/backend/atlas_plugin_c4/permissions.py:29` — `DIAGRAM_READ_PERMISSION` (read-only; still must pass through the facade so `.read` semantics stay centralized).
6. `plugins/flows/backend/atlas_plugin_flows/permissions.py:23` — `FLOW_EDIT_PERMISSION` against the owning System.
7. `core/backend/server/apps/catalog/tests/test_authentication.py:223,227,245` — direct test call sites against the real `policy_evaluator` singleton; not production code, but will need updating once the singleton is replaced/wrapped by the facade (or these tests need to move to constructing the facade explicitly).

### Direct-evaluator-bypass call sites (must get the *same* shared guard even though they never call `.check`)

1. **`EntityWritePermission.check_create`** (`core/backend/server/apps/catalog/api/permissions.py:44-46`) — calls `is_group_member(user, owner)` directly; never touches `policy_evaluator`. Called from `EntityService.create` (`entity_service.py:216`) whenever `source != SOURCE_YAML`. This is design.md Decision 1's explicit example ("resource-less entity creation").
2. **`TagWritePermission.check_write`** (`api/permissions.py:80-83`) — raw `request.user.is_superuser`. Called from `TagDetailController.patch` (`views.py:248`).
3. **`CatalogHomeSettingsWritePermission.check_write`** (`api/permissions.py:94-97`) — same raw `is_superuser` pattern. Called from `CatalogHomeSettingsController.patch` (`views.py:269`).
4. **`has_purge_grant`** (`authorization.py:46-61`) — not itself bypassed (only reached through `RBACPolicyEvaluator.check`'s `.purge` branch, i.e. already behind call site #3 above), but its own `principal.is_superuser` shortcut (`:57-58`) is a privilege shortcut that must be evaluated *after* the facade's read-only denial, per design.md Decision 1 ("A helper that answers whether purge is authorized must apply the same guard before privilege shortcuts") — i.e. the facade wraps the whole `RBACPolicyEvaluator.check` call, not something inserted inside it.
5. **`DatabaseSchemaController.post`/`.patch`** (§1.1.D above) — no check at all today; once a check is added (task 3.4/necessary prerequisite), it must go through the shared guard from day one rather than being added unguarded and revisited later.
6. Django admin's default `has_add_permission`/`has_change_permission`/`has_delete_permission` (Django's own `ModelAdmin` machinery, no single file — see §1.1.E) — not a "call site" in the grep sense, but conceptually the same category: authorization happening entirely outside `policy_evaluator`.

### Facade placement sketch (for task 3.2)

`PolicyEvaluator.check(principal, permission, resource) -> bool` cannot change
shape (design.md, spec). The natural seam is where the singleton is currently
exposed to two different audiences:

- **Core-internal**: `server.apps.catalog.authorization.policy_evaluator` (the module-level instance, `authorization.py:125`). Every internal call site (#1-3 above) already goes through `EntityWritePermission`'s classmethods rather than importing `policy_evaluator` ad hoc — so wrapping is possible either by (a) replacing the module-level `policy_evaluator` binding itself with a `CoreGuardedEvaluator(RBACPolicyEvaluator())` instance (zero call-site changes, since everything already goes through the module attribute), or (b) wrapping only inside `EntityWritePermission`'s three classmethods. (a) is preferable — it also automatically covers `bind_policy_evaluator(policy_evaluator)` in `plugin.py:47`, so the plugin-facing side gets the guarded instance for free without a second wrapping step.
- **Plugin-facing**: `atlas_plugin_api.get_policy_evaluator()` (`permissions.py:126-139`) already returns whatever was bound via `bind_policy_evaluator()` — if Core binds the *guarded* facade instance there (per (a) above), every plugin call site (#4-6) is covered with no plugin-side code change, satisfying design.md Decision 1 ("Core and `get_policy_evaluator()` consumers receive this facade, never the raw selected implementation") for free.
- **Direct-bypass sites** (`check_create`, `TagWritePermission`, `CatalogHomeSettingsWritePermission`, and the future `DatabaseSchemaController` check) cannot be covered by wrapping the evaluator singleton, since they never call `.check(...)` at all. These need one shared predicate/helper — e.g. `require_not_read_only(principal)` — called explicitly at the top of each, plus reused *inside* the guarded evaluator wrapper for the `.check(...)` path so there's exactly one implementation of "is this principal currently read-only," not two.
- The wrapper's `.check()` needs the permission-effect classification (task 3.1) to decide "read → delegate unconditionally" vs. "write/unknown → deny if read-only, else delegate" — for `<kind>.read/.edit/.create/.delete/.purge` it can pattern-match the suffix directly (per the design gap noted above); for anything else it must consult the (new) effect metadata on `PermissionRegistry`.

## Summary

- **Mutation sites inventoried**: ~30 distinct HTTP mutation endpoints (entity CRUD ×5 kinds ×~6 ops, 2 relationship endpoints, 2 direct-superuser endpoints, 4 dependency-link endpoints, 2 unguarded facet endpoints, 3 Flow endpoints) + all Django admin registrations (10 models, all default add/change/delete, no custom actions).
- **Guarded via `policy_evaluator`/`EntityWritePermission.check_write|check_adopt|check_purge`**: the large majority — all per-kind update/adopt/remove/revive/delete/purge across Systems/Components/Resources/APIs, plus the 4 plugin dependency-link endpoints and Flow edit/delete.
- **Guarded but bypassing the evaluator (direct-check sites needing the shared guard)**: 3 — `EntityWritePermission.check_create`, `TagWritePermission.check_write`, `CatalogHomeSettingsWritePermission.check_write`.
- **Completely unguarded today**: 1 — `DatabaseSchemaController.post`/`.patch` (pre-existing gap, any authenticated user, not just read-only-relevant).
- **Django admin**: every model's add/change/delete relies on Django's own permission system, not `policy_evaluator` — needs its own shared-predicate hook (no existing hook to extend).
- **Background jobs**: none exist in the codebase; task 4.2/7.7 are forward-looking contract requirements, not fixes to an existing enqueue call site.

## Release coverage verification (task 9.6)

Re-scanned the completed distribution on 2026-09-20 before declaring the
change complete. The current controller scan contains the same mutation
families recorded above: standard-catalog and API entity lifecycle operations,
Core architecture relationships/tags/home settings, API dependency links,
the Database Schema facet, and Flow create/edit/delete. Each reaches either
`EntityWritePermission`, the Core-guarded public evaluator, or a direct shared
`is_account_read_only` guard before mutation.

The admin scan now also finds the API endpoint/operation
`mark_as_removed` bulk actions, which were added after the original inventory
was written. They are covered by the global read-only `ModelAdmin.get_actions`
guard and the crafted bulk/custom-action regression in
`test_read_only_admin.py`. All other registered admin models are covered by
the shared `BaseModelAdmin` add/change/delete guards and inline checks.

The asynchronous-work scan still finds no Celery/RQ enqueue, `.delay()`, or
`apply_async()` call site. Scheduled ingestion remains the independently
authorized service path described above. The current mutation inventory has
no uncovered user-triggered entry point; adding a controller, admin action, or
job dispatcher requires extending this inventory and its negative regression
coverage.
