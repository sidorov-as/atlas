"""Composition validation.

Runs once, synchronously, right after the runtime entry-point-loading
phase and before the process accepts traffic. Each
registry (`EntityKindRegistry`, `CapabilityRegistry`, `PermissionRegistry`)
already rejects a duplicate id the instant a second plugin tries to claim
it, naming both registering plugins — `validate_composition` is the single
place that runs the load phase and turns any of those into one
`CompositionError`, so the startup orchestration has one
exception type to catch and turn into a non-zero exit before binding a
port.

Missing required capability/dependency detection is a stub for now,
filled in once a real cross-plugin capability consumer exists
(such as the C4 plugin).

`CompositionError` itself has no Django-model imports, unlike the rest of
this module — `startup.bootstrap()` imports it before `django.setup()`
has run, to have the exception type ready for its `try`/`except` around
that call.
"""

from collections.abc import Iterable

from atlas_plugin_api import PluginDescriptor

REQUIRED_PLUGINS = frozenset({"atlas.standard-catalog"})
"""Plugin ids the official Atlas distribution cannot omit from
`SELECTED_PLUGINS`.
Stands in for a real deployment-manifest "required plugin" concept until
a distribution composer takes over."""


class CompositionError(Exception):
    """Raised when composition validation fails."""


def _check_required_plugins(
    descriptors: Iterable[PluginDescriptor],
    required_plugins: frozenset[str],
) -> None:
    selected_ids = {descriptor.id for descriptor in descriptors}
    missing = required_plugins - selected_ids
    if missing:
        raise CompositionError(
            "Required plugin(s) missing from SELECTED_PLUGINS: "
            f"{', '.join(sorted(missing))}",
        )


def _check_plugin_dependencies(descriptors: Iterable[PluginDescriptor]) -> None:
    """Each selected plugin's `requires_plugins` id must also be selected
    (`docs/plugin-architecture.md`'s `requires.plugins`).
    Version-range compatibility has no source of truth
    to check against yet (matching `resolver.verify_selected_descriptors`'s
    same deferral), so only presence is checked."""
    selected_ids = {descriptor.id for descriptor in descriptors}
    for descriptor in descriptors:
        missing = set(descriptor.requires_plugins) - selected_ids
        if missing:
            raise CompositionError(
                f"{descriptor.id!r} requires plugin(s) missing from "
                f"SELECTED_PLUGINS: {', '.join(sorted(missing))}",
            )


def validate_composition(
    descriptors: Iterable[PluginDescriptor],
    *,
    required_plugins: frozenset[str] = REQUIRED_PLUGINS,
    disabled_ids: frozenset[str] = frozenset(),
) -> None:
    """`required_plugins` defaults to the real official-distribution
    requirement; tests exercising composition mechanics with synthetic
    fixture plugins that aren't meant to represent a full distribution pass
    `frozenset()` instead.

    `disabled_ids` is still checked against
    `required_plugins`/dependencies as normal — `disabled` keeps a plugin
    selected (its code installed), unlike `removed`, so it satisfies
    another plugin's dependency the same way an active one does; it's only
    passed through to skip that plugin's own registration loading."""
    # Deferred: `DuplicateKindError` transitively imports Django models
    # (via the Entity Kind registry), unsafe before `django.setup()`.
    from server.apps.catalog.kinds.registry import DuplicateKindError
    from server.apps.plugins.capabilities import DuplicateCapabilityError
    from server.apps.plugins.permissions import DuplicatePermissionError
    from server.apps.plugins.runtime import load_runtime_entry_points

    descriptors = tuple(descriptors)
    _check_required_plugins(descriptors, required_plugins)
    _check_plugin_dependencies(descriptors)

    duplicate_id_errors = (
        DuplicateKindError,
        DuplicateCapabilityError,
        DuplicatePermissionError,
    )
    try:
        load_runtime_entry_points(descriptors, disabled_ids=disabled_ids)
    except duplicate_id_errors as exc:
        raise CompositionError(str(exc)) from exc
