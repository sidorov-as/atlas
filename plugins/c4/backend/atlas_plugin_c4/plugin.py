"""Static plugin descriptor for the C4 plugin.

PlantUML rendering, the diagram endpoints, viewer preferences, and the C4/
System Architecture detail tabs live here, split out of `server.apps.catalog`
(the first plugin that must target *which entities support
diagrams* semantically... instead of hard-coding kind === 'system' or kind
=== 'component').

Optional in the official distribution: a distribution
selecting `atlas.standard-catalog` but not `atlas.c4` must still compose —
`atlas.c4` is absent from `server.apps.plugins.composition.REQUIRED_PLUGINS`.
It declares a required manifest dependency on `atlas.standard-catalog`
(System/Component/Resource/Group data diagrams read) — `atlas.apis` is only
an optional, code-level dependency (API entities may appear in diagrams when
present), not a `requires_plugins` entry, since `PluginDescriptor` has no
"optional dependency" concept (composition.py `_check_plugin_dependencies`
treats every `requires_plugins` entry as mandatory).
"""

from atlas_plugin_api import PluginDescriptor

PLUGIN = PluginDescriptor(
    id="atlas.c4",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("atlas_plugin_c4",),
    entry_point="atlas_plugin_c4.plugin:PLUGIN",
    requires_plugins={"atlas.standard-catalog": ">=0.1 <1"},
)

DIAGRAM_READ_PERMISSION = "atlas.c4.diagram.read"


def register_runtime() -> None:
    """Populate this plugin's runtime registrations.

    Called by the shared "load selected runtime entry points" phase
    (`server.apps.plugins.runtime.load_runtime_entry_points`), after
    `django.setup()` — never at import time.
    """
    from atlas_plugin_api import register_permission

    register_permission(DIAGRAM_READ_PERMISSION, owner=PLUGIN.id)
