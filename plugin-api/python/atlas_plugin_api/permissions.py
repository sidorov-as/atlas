"""Permission registration and authorization-check contract:
Core publishes its plugin-facing
surface as contract types.

Stands in for `server.apps.plugins.permissions` (the permission-id registry)
and `server.apps.catalog.authorization.policy_evaluator` (the singleton
`PolicyEvaluator` extension point, ADR 0016) — a plugin declares a
permission id it checks through `register_permission()`, and checks whether
a principal holds it through `get_policy_evaluator().check(...)`, instead of
importing either module directly.

`PermissionRegistry` (unlike `PolicyEvaluator`) needs no Django model, so
(like `kinds.py`'s `EntityKindRegistry`) it moves here outright:
`atlas_plugin_api` owns the mechanism, and `server.apps.plugins.permissions`
re-exports it for Core's own internal call sites
The real `PolicyEvaluator`,
by contrast, does real Django ORM work against the concrete `CatalogEntity`
model (`is_group_member`'s `group_details.members.filter(...)`), which
`atlas_plugin_api` structurally cannot import (`core/backend` is
`package-mode = false` — catalog.py's docstring), so it stays in
`server.apps.catalog.authorization` and is handed to `atlas_plugin_api` via
`bind_policy_evaluator()` — the same "Core registers the singleton,
`atlas_plugin_api` structurally can't import it" shape as
`entity_service.py`'s `bind_entity_service()`/`get_entity_service()`.

`get_policy_evaluator()` returns Core's guarded facade, never a raw selected evaluator, so a plugin's
mutation checks are automatically denied for a read-only Principal without
the plugin doing anything itself beyond registering its permission ids
(`register_permission`) and using `.check(...)` — a plugin must not call
`is_superuser` directly or claim a service/system identity to check
permissions on the caller's behalf, either of which would route around
this facade). This contract governs a *trusted*,
installed server plugin's own mutation checks — it is not a sandbox, and
does not protect against a malicious plugin implementation choosing not
to call it at all (the same
"installed plugins are trusted server code" boundary the wider plugin
architecture assumes throughout).
"""

from typing import Any, Literal, Protocol, runtime_checkable

from .catalog import CatalogEntity

PermissionEffect = Literal["read", "write"]

#: Core's own per-Entity-Kind permission suffixes (`f'{kind}.read'`,
#: `f'{kind}.edit'`, etc. — `server.apps.catalog.api.permissions`,
#: `server.apps.catalog.authorization.RBACPolicyEvaluator`). Core never
#: calls `register_permission()` for these (Core has no registration call site of
#: its own), so a permission ending in one of these suffixes is classified
#: structurally, before consulting `PermissionRegistry` at all — otherwise
#: the fail-closed "unregistered is write" rule below would deny every
#: read on every entity, not just writes.
_STANDARD_READ_SUFFIXES = (".read",)
_STANDARD_WRITE_SUFFIXES = (".edit", ".create", ".delete", ".purge")


class InvalidPermissionEffectError(ValueError):
    """Raised when `register_permission`/`PermissionRegistry.register` is
    given an `effect` that isn't `'read'` or `'write'`."""

    def __init__(self, permission_id: str, effect: str) -> None:
        super().__init__(
            f"Invalid effect={effect!r} for permission_id={permission_id!r}; "
            "must be 'read' or 'write'",
        )
        self.permission_id = permission_id
        self.effect = effect


class DuplicatePermissionError(ValueError):
    """Raised when a second plugin tries to register a claimed `permission_id`.

    `existing_owner`/`new_owner` carry the registering plugins' ids, when
    known, for composition-validation error reporting.
    """

    def __init__(
        self,
        permission_id: str,
        *,
        existing_owner: str | None = None,
        new_owner: str | None = None,
    ) -> None:
        message = (
            f"A permission is already registered for permission_id={permission_id!r}"
        )
        if existing_owner or new_owner:
            message += (
                f" (already registered by {existing_owner!r}, "
                f"conflicting registration from {new_owner!r})"
            )
        super().__init__(message)
        self.permission_id = permission_id
        self.existing_owner = existing_owner
        self.new_owner = new_owner


class PermissionRegistry:
    """Tracks the flat set of registered `permission_id`s and each
    one's read/write `effect`. `effect_for()` is only ever consulted for a nonstandard-suffix id
    — see `classify_permission_effect()`, the guard's actual entry point.
    """

    def __init__(self) -> None:
        self._owners: dict[str, str | None] = {}
        self._effects: dict[str, PermissionEffect] = {}

    def register(
        self,
        permission_id: str,
        *,
        owner: str | None = None,
        effect: PermissionEffect | None = None,
    ) -> None:
        if permission_id in self._owners:
            raise DuplicatePermissionError(
                permission_id,
                existing_owner=self._owners[permission_id],
                new_owner=owner,
            )
        if effect is not None and effect not in ("read", "write"):
            raise InvalidPermissionEffectError(permission_id, effect)
        self._owners[permission_id] = owner
        self._effects[permission_id] = effect or (
            "read" if permission_id.endswith(_STANDARD_READ_SUFFIXES) else "write"
        )

    def is_registered(self, permission_id: str) -> bool:
        return permission_id in self._owners

    def registered_ids(self) -> list[str]:
        """Return every registered `permission_id`, sorted."""
        return sorted(self._owners)

    def effect_for(self, permission_id: str) -> PermissionEffect | None:
        """Return the registered effect for `permission_id`, or `None` if
        it was never registered."""
        return self._effects.get(permission_id)


# Process-wide registry populated by the runtime entry-point-loading phase.
registry = PermissionRegistry()


def register_permission(
    permission_id: str,
    *,
    owner: str | None = None,
    effect: PermissionEffect | None = None,
) -> None:
    """Register `permission_id` as one a plugin declares and checks

    `effect` declares whether
    holding this permission lets a read-only Principal use it: omit it for
    the compatible default (`.read`-suffixed ids default to read,
    everything else to write), or pass `'read'` explicitly for a
    nonstandard-suffixed, side-effect-free query (e.g. `.execute`/`.sync`
    that only reads). Most registered ids never need this — see
    `classify_permission_effect()`.

    Called from a plugin's `register_runtime()` hook, during the shared
    runtime entry-point-loading phase, after `django.setup()`.
    """
    registry.register(permission_id, owner=owner, effect=effect)


def classify_permission_effect(permission_id: str) -> PermissionEffect:
    """Classify `permission_id` as `'read'` or `'write'` for the Core
    read-only guard.

    Core's own per-kind ids (`<kind>.read/.edit/.create/.delete/.purge`)
    are classified structurally by suffix, without consulting the
    registry — Core never registers them (see `_STANDARD_*_SUFFIXES`'s
    docstring), and every plugin-registered id ending in one of these five
    suffixes already gets the identical classification for free this way
    too, so the registry only needs consulting for a nonstandard suffix. A
    nonstandard-suffixed id that was never registered, or registered
    without an explicit effect, defaults to write and is denied for a
    read-only caller — "fail closed".
    """
    if permission_id.endswith(_STANDARD_READ_SUFFIXES):
        return "read"
    if permission_id.endswith(_STANDARD_WRITE_SUFFIXES):
        return "write"
    return registry.effect_for(permission_id) or "write"


@runtime_checkable
class PolicyEvaluator(Protocol):
    """Decides whether `principal` holds `permission` on `resource`
    (plugin-architecture.md:449-453's call shape)."""

    def check(
        self,
        principal: Any,
        permission: str,
        resource: CatalogEntity | None,
    ) -> bool: ...


_policy_evaluator: PolicyEvaluator | None = None


def bind_policy_evaluator(evaluator: PolicyEvaluator) -> None:
    """Core-only: register the real `PolicyEvaluator` singleton, so
    `get_policy_evaluator()` can hand it out without `atlas_plugin_api` ever
    importing `server`. Called once from `server.apps.catalog.plugin.
    register_runtime()`, during the shared runtime entry-point-loading
    phase (`server.apps.plugins.runtime`), before any request is served.
    """
    global _policy_evaluator
    _policy_evaluator = evaluator


def get_policy_evaluator() -> PolicyEvaluator:
    """Return the process-wide `PolicyEvaluator` singleton Core registered
    via `bind_policy_evaluator()`. Only callable after that registration has
    run — from inside a function body or method, never cached at plugin
    module import time (matching `get_entity_service()`'s same caution).
    """
    if _policy_evaluator is None:
        msg = (
            "get_policy_evaluator() called before Core registered its "
            "PolicyEvaluator singleton (server.apps.catalog.plugin."
            "register_runtime() must run first)"
        )
        raise RuntimeError(msg)
    return _policy_evaluator
