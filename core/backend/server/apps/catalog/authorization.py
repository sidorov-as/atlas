"""Core Authorization Service (ADR 0016).

A `singleton` extension point (plugin-architecture.md's cardinality model:
"exactly one selected implementation") — unlike `AuthenticationProvider`'s
`keyed` collection, a deployment selects exactly one `PolicyEvaluator` and
every permission check, core or plugin-declared, is delegated to it
(`authorization.check(principal=..., permission=..., resource=...)`,
plugin-architecture.md:449-453).

`RBACPolicyEvaluator` is a literal extraction of what was previously
`EntityWritePermission.is_group_member`'s inline ownership check (no
behavior change): superuser writes always pass; a `<kind>.edit` permission
requires membership (via `catalog_actor`) in `resource.owner`; `.read` —
including `atlas.c4.diagram.read`, formerly served by C4's
`AlwaysAllowIfAuthenticated` stand-in — is granted to any authenticated
principal regardless of resource.

`.create`/`.delete` (`atlas.apis.endpointDependency`/`operationDependency`
`.create`/`.delete`)
share `.edit`'s ownership check when a `resource` is given: the caller passes
the consuming `Service` (not the Endpoint/Operation being linked), so
authorization turns on owning *your own* Service, never on membership in the
Endpoint/Operation's owner Group (prerelease security audit finding — a
plain authenticated user could otherwise link or unlink any Service to any
Endpoint/Operation, including ones owned by teams they have nothing to do
with). A `.create`/`.delete` check made with `resource=None` still falls
back to unrestricted-if-authenticated, matching `.read`, for the case
originally described — a resource with genuinely no
owner to check membership against — though no permission in the codebase
currently does this. It is shipped as the default (and, for now, only)
evaluator; an OPA-backed evaluator is a documented Non-Goal, not
built here.

`PolicyEvaluator`/`policy_evaluator` below are re-exported by
`atlas_plugin_api.permissions` for static typing (`PolicyEvaluator`) and
registered with it via `server.apps.catalog.plugin.register_runtime()`'s
`bind_policy_evaluator()` call — a plugin checks a permission through
`atlas_plugin_api.get_policy_evaluator()`, not by importing `policy_evaluator`
from here directly. It can't move outright the way `EntityKindRegistry` did:
`RBACPolicyEvaluator`/`is_group_member` do real Django ORM work against the
concrete `CatalogEntity` model, which `atlas_plugin_api` structurally cannot
import (`core/backend` is `package-mode = false`).
"""

from typing import Any, Protocol

from atlas_plugin_api import classify_permission_effect
from django.db import Error as DjangoDatabaseError

from server.apps.catalog.membership import is_effective_member
from server.apps.catalog.models import AccountAccess, CatalogEntity, PurgeGrant


def is_account_read_only(principal: Any | None) -> bool:
    """Shared account-state predicate: a missing `AccountAccess` row means
    `False` (compatibility — most
    accounts never get one); a query failure fails *closed* (`True`) rather
    than silently behaving as an unrestricted account. Always hits the
    database directly — no session or process-wide cache, so a flag change
    is observed by the very next call.

    Every write guard (the guarded evaluator facade, the direct-check
    bypass sites, Django admin, job dispatch) must call this one function
    rather than reimplement the missing-row/fail-closed rule itself.
    """
    if not principal or not getattr(principal, "pk", None):
        return False
    try:
        read_only = (
            AccountAccess.objects.filter(
                account=principal,
            )
            .values_list("read_only", flat=True)
            .first()
        )
    except DjangoDatabaseError:
        return True
    return bool(read_only)


def has_purge_grant(
    principal: Any,
    group: CatalogEntity | None,
) -> bool:
    """Built-in RBAC Purge-Grant rule (a Purge Grant is scoped per
    owner-Group with a global-admin override): a
    read-only is denied before either privilege shortcut; otherwise a global
    admin needs no grant and may Purge regardless of `group`/`source_kind`,
    while any other `principal` must hold a `PurgeGrant` row scoped to
    `group`. Plain owner-Group membership (`is_group_member`) is *not*
    sufficient (a Purge Grant does not authorize edits or
    remove/revive, symmetrically — edit/remove/revive membership doesn't
    authorize Purge either)."""
    if is_account_read_only(principal):
        return False
    if principal.is_superuser:
        return True
    if group is None:
        return False
    return PurgeGrant.objects.filter(group=group, grantee=principal).exists()


def is_group_member(
    principal: Any,
    group: CatalogEntity | None,
) -> bool:
    """Built-in RBAC ownership-membership rule, moved verbatim from
    `EntityWritePermission.is_group_member`."""
    if principal.is_superuser:
        return True
    if group is None:
        # Ownerless kinds (Group/Actor themselves):
        # only superusers may write them, since there's no owner Group to
        # check membership against.
        return False
    catalog_actor = getattr(principal, "catalog_actor", None)
    if catalog_actor is None:
        return False
    group_details = getattr(group, "group_details", None)
    if group_details is None:
        return False
    return is_effective_member(actor=catalog_actor.entity, group=group_details)


class PolicyEvaluator(Protocol):
    """Decides whether `principal` holds `permission` on `resource`
    (plugin-architecture.md:449-453's call shape)."""

    def check(
        self,
        principal: Any,
        permission: str,
        resource: CatalogEntity | None,
    ) -> bool: ...


class RBACPolicyEvaluator:
    """Built-in RBAC evaluator: reproduces today's exact
    ownership-based edit rule plus unrestricted read for any authenticated
    principal, now served from one shared decision point instead of
    kind-specific view logic. `.create`/`.delete` share `.edit`'s ownership
    check whenever a caller passes a `resource` (module docstring)."""

    def check(
        self,
        principal: Any,
        permission: str,
        resource: CatalogEntity | None,
    ) -> bool:
        if permission.endswith(".purge"):
            # Purge Grant, not superuser-first (scoped per
            # owner-Group with a global-admin override)
            # — `has_purge_grant` already recognizes `is_superuser` as its own
            # override, so this doesn't fall through the plain superuser check
            # above it the way `.edit`/`.read`/etc. do.
            return has_purge_grant(
                principal,
                resource.owner if resource else None,
            )
        if principal.is_superuser:
            return True
        if permission.endswith(".edit"):
            return is_group_member(
                principal,
                resource.owner if resource else None,
            )
        if permission.endswith((".create", ".delete")):
            # Ownership-scoped exactly like `.edit` whenever the caller can
            # supply a resource to check ownership against — e.g. the
            # consuming Service for `endpointDependency`/`operationDependency`
            # `.create`/`.delete` (module docstring: prerelease security audit
            # finding). Only a `resource=None` check — a permission with no
            # ownable resource to check at all — falls
            # back to `.read`'s unrestricted-if-authenticated rule.
            if resource is None:
                return bool(principal and principal.is_authenticated)
            return is_group_member(principal, resource.owner)
        if permission.endswith(".read"):
            return bool(principal and principal.is_authenticated)
        return False


class CoreGuardedEvaluator:
    """Mandatory Core restriction wrapping the selected `PolicyEvaluator`
    (the Authorization Service presents a Core-guarded facade around the
    selected PolicyEvaluator.
    Core and `atlas_plugin_api.get_policy_evaluator()` consumers receive
    this facade, never the raw selected implementation).

    Denies before delegating whenever `principal` is read-only and
    `permission` classifies as write/unknown (`classify_permission_effect`)
    — so this also runs *before* the inner evaluator's own privilege
    shortcuts (`is_superuser`, `has_purge_grant`'s superuser override),
    satisfying "Core enforces the read-only override before write
    privileges" without either of those
    functions needing to know about read-only themselves. A non-read-only
    principal, or a read-only principal requesting a read permission, is
    delegated to `_inner` exactly as before — normal-account behavior and
    read access are unchanged: ordinary read
    decisions and non-read-only behavior still go to the selected
    evaluator.
    """

    def __init__(self, inner: PolicyEvaluator) -> None:
        self._inner = inner

    def check(
        self,
        principal: Any,
        permission: str,
        resource: CatalogEntity | None,
    ) -> bool:
        effect = classify_permission_effect(permission)
        if effect == "write" and is_account_read_only(principal):
            return False
        return self._inner.check(principal, permission, resource)


# Process-wide selected evaluator — the "singleton" extension point's current
# selection. Deployment-config-driven selection among multiple registered
# evaluators is out of scope here; this is the sole,
# default-selected implementation. Wrapped in `CoreGuardedEvaluator` so every
# consumer of this module attribute — including `bind_policy_evaluator()`
# below, which hands the *same* instance to `atlas_plugin_api.
# get_policy_evaluator()` — receives the guarded facade, never
# `RBACPolicyEvaluator` (or a future alternate selected evaluator) directly.
policy_evaluator: PolicyEvaluator = CoreGuardedEvaluator(RBACPolicyEvaluator())
