# Permissions

Every Atlas permission check, whether core-owned or plugin-declared, goes through one call:

```python
get_policy_evaluator().check(principal, permission_id, resource)
```

`PolicyEvaluator` is a `singleton` extension point: a deployment selects exactly one
implementation that decides *every* permission, including plugin-declared permissions. Plugins
cannot add their own authorization logic or a parallel role system. See [Authorization is
centralized](principles.md#authorization-is-centralized-across-plugins).

The public evaluator is a Core-guarded facade around the selected implementation. Before
delegation, Core denies a read-only Principal when the permission has write effect. This mandatory
restriction applies before ownership, superuser, or Purge Grant shortcuts; changing evaluators
cannot bypass it. Read-only status does not grant a read that the selected evaluator would deny.

## Declaring a permission id

A permission id is just a string, in one of two shapes:

- **Core-owned**, one per Entity Kind action: `<kind>.read`, `<kind>.create`, `<kind>.edit`,
  `<kind>.delete` (e.g. `component.edit`).
- **Plugin-declared**, namespaced by plugin id: `atlas.<plugin>.<resource>.<action>` (e.g.
  `atlas.apis.endpointDependency.create`, `atlas.c4.diagram.read`).

A plugin registers the id during `register_runtime()`:

```python
from atlas_plugin_api import register_permission

register_permission(ENDPOINT_DEPENDENCY_CREATE_PERMISSION, owner=PLUGIN.id)
```

A second plugin that claims an already-registered id fails composition. The error names the
existing owner and the conflicting registration, following the same "fail loudly at composition
time" guarantee used for duplicate Entity Kind and route ids (see
[Assembling a distribution](../configuration/distributions.md#what-gets-rejected-before-it-ships)).
Registering an id does not decide who holds it. That is the selected `PolicyEvaluator`'s decision.

Registration also accepts `effect="read"` or `effect="write"`. Registered ids ending in `.read`
default to read; every other registered id defaults to write, including `.execute` and `.sync`.
An explicitly read custom permission must describe a side-effect-free operation and have contract
coverage. Unknown permissions fail closed for read-only callers.

Authentication providers do not participate in permission decisions. Claims,
roles, scopes, and external groups can produce ordinary provider-owned Group
grants only through explicit Core mappings. The evaluator reads effective
membership, which may be supported by manual and provider grants at the same
time. Staff, superuser, Purge Grant, and `AccountAccess.read_only` remain
separate operator-managed state. See [Authentication and identity](auth-and-identity.md).

## The built-in evaluator: role-based access control

Atlas ships `RBACPolicyEvaluator`, which is selected by default. An OPA-backed or other external
evaluator is a documented non-goal; Core does not impose that restriction. Its decision
procedure is:

1. The Core read-only guard denies write-effect permissions before this evaluator runs.
2. For an unrestricted Principal, superuser status passes ordinary evaluator checks; Purge uses
   its separately scoped grant rule.
3. A permission ending `.edit` is granted only if the Principal's linked Actor
   (`principal.catalog_actor`) is a member of `resource.owner`, the Group that owns the entity
   being edited. No linked Actor, or no membership, means denied. A `resource` with no owner at
   all (only Group and Actor entities have none) can only ever be edited by a superuser, since
   there's no owner Group to check membership against.
4. A permission ending `.read`, `.create`, or `.delete` is granted to *any* authenticated
   Principal, regardless of `resource`. This is deliberately unrestricted, so
   `atlas.apis.endpointDependency.create`/`.delete` and `atlas.c4.diagram.read` work with
   `resource=None`: the underlying records they gate (a `ServiceEndpointUsage` link, a rendered
   diagram) have no owner of their own for a narrower rule to check against.
5. Anything else is denied.

A permission that needs a rule narrower than "any authenticated principal" but has no owning Group
to check has no branch to use today. It requires a new evaluator instead of a
special case in this one.

## YAML-managed entities are provenance-blocked, not permission-blocked

A write to an entity with `source_kind=yaml` is rejected *before* `PolicyEvaluator.check` is
called, including for superusers. Whether an entity accepts a manual write depends on where its
data comes from. That is a provenance question, separate from permissions. See [Life of an
entity](life-of-an-entity.md#yaml-ingestion-and-claim-arbitration) for the arbitration rules that
decide `source_kind`, and [Adoption](life-of-an-entity.md#adoption) for the
write that is permission-gated while an entity moves into YAML management. Adopting an entity uses
the same `<kind>.edit` decision as any other edit.

## What operators can't configure yet

The deployment manifest cannot select a different `PolicyEvaluator` or tune
`RBACPolicyEvaluator`'s rules. The built-in evaluator is currently the only implementation.
An alternative requires an implementation of the `PolicyEvaluator` protocol (`check(principal,
permission, resource) -> bool`) wired in as core's singleton. It cannot be configured in the
distribution manifest.

For the operator workflow, live-session behavior, and recovery boundary, see
[Manage read-only accounts](../operating-atlas/read-only-accounts.md).
