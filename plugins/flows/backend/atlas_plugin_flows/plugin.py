"""Static plugin descriptor for the Flows plugin.

Flow — the hand-authored, ordered cross-system process documentation feature
— lives here, split out of `server.apps.catalog` (Flow was named
alongside System/Component/Resource/API/C4 as a module a later change would
split out of the in-tree "core" plugin, but never got one until now).

Optional in the official distribution: a distribution selecting `atlas.standard-catalog` but
not `atlas.flows` must still compose — `atlas.flows` is absent from
`server.apps.plugins.composition.REQUIRED_PLUGINS`. It declares a manifest
dependency on `atlas.standard-catalog` (Flow's `system` field resolves a
System entity), the same shape `atlas.apis`/`atlas.c4` declare.
"""

from atlas_plugin_api import PluginDescriptor

PLUGIN = PluginDescriptor(
    id="atlas.flows",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("atlas_plugin_flows",),
    entry_point="atlas_plugin_flows.plugin:PLUGIN",
    requires_plugins={"atlas.standard-catalog": ">=0.1 <1"},
)


def register_runtime() -> None:
    """Populate this plugin's runtime registrations.

    Called by the shared "load selected runtime entry points" phase
    (`server.apps.plugins.runtime.load_runtime_entry_points`), after
    `django.setup()` — never at import time.
    """
    from atlas_plugin_api import (
        register_permission,
        register_purge_scanner,
        register_search_source,
    )

    from atlas_plugin_flows.models import scan_flow_purge_references
    from atlas_plugin_flows.permissions import (
        FLOW_EDIT_PERMISSION,
        FLOW_READ_PERMISSION,
    )
    from atlas_plugin_flows.search_source import flow_search_source

    register_permission(FLOW_READ_PERMISSION, owner=PLUGIN.id)
    register_permission(FLOW_EDIT_PERMISSION, owner=PLUGIN.id)
    register_purge_scanner(PLUGIN.id, scan_flow_purge_references)
    # Harmless without the search plugin: nothing reads the registry then.
    register_search_source(flow_search_source, owner=PLUGIN.id)
