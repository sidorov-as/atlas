"""Per-plugin runtime health tracking (`runtime-failure-isolation` spec:
"A health/diagnostics endpoint SHALL report each installed plugin's status,
distinguishing healthy from degraded").

A plugin starts `active`; `mark_degraded` — called by `error_handling.
global_error_handler` when an unhandled exception reaches one of that
plugin's endpoints — flips it to `degraded` for the rest of this process's
lifetime. This deliberately doesn't try to auto-recover a plugin back to
`active`: ADR 0020 isolates and surfaces a runtime failure, it doesn't
paper over it, so an operator sees "this plugin threw at some point" until
the process restarts. `disabled` (the lifecycle spec's manifest flag) is
reported distinctly from `degraded` — it's a deliberate operator state, not
a failure.
"""

import threading
from dataclasses import dataclass

from django.apps import apps as django_apps

from server.apps.plugins.resolver import load_selected_descriptors
from server.settings.selected_plugins import DISABLED_PLUGINS, SELECTED_PLUGINS


class _DegradedPluginTracker:
    """Process-wide, thread-safe record of which plugins have hit an
    unhandled runtime exception since this process started."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reasons: dict[str, str] = {}

    def mark_degraded(self, plugin_id: str, reason: str) -> None:
        with self._lock:
            self._reasons[plugin_id] = reason

    def reason_for(self, plugin_id: str) -> str | None:
        with self._lock:
            return self._reasons.get(plugin_id)

    def reset(self) -> None:
        """Test-only: clear every recorded failure."""
        with self._lock:
            self._reasons.clear()


_tracker = _DegradedPluginTracker()
mark_degraded = _tracker.mark_degraded
reset_degraded = _tracker.reset


def plugin_id_for_module(module_path: str) -> str | None:
    """Resolve the plugin id owning `module_path` (a failing controller's
    `__module__`, typically), via the Django app config that contains it."""
    app_config = django_apps.get_containing_app_config(module_path)
    if app_config is None:
        return None
    return _plugin_by_app_label().get(app_config.label)


def _plugin_by_app_label() -> dict[str, str]:
    """Map each selected plugin's Django app label(s) to its plugin id —
    same convention as `check_migration_boundaries`'s and `purge_plugin`'s
    own copy of this mapping."""
    configs_by_name = {
        config.name: config for config in django_apps.get_app_configs()
    }
    mapping: dict[str, str] = {}
    for descriptor in load_selected_descriptors(SELECTED_PLUGINS):
        for app_name in descriptor.django_apps:
            app_config = configs_by_name.get(app_name)
            if app_config is not None:
                mapping[app_config.label] = descriptor.id
    return mapping


@dataclass(frozen=True, slots=True)
class PluginHealth:
    id: str
    status: str
    """One of `active`, `disabled`, `degraded`."""


def plugin_health() -> list[PluginHealth]:
    """Every selected plugin's current health, `disabled` taking precedence
    over any recorded runtime failure for reporting purposes (an operator
    who disabled a plugin already knows its state)."""
    statuses = []
    for descriptor in load_selected_descriptors(SELECTED_PLUGINS):
        if descriptor.id in DISABLED_PLUGINS:
            status = "disabled"
        elif _tracker.reason_for(descriptor.id) is not None:
            status = "degraded"
        else:
            status = "active"
        statuses.append(PluginHealth(id=descriptor.id, status=status))
    return statuses
