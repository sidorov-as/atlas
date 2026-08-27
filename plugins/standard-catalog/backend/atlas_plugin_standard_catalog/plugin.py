"""Static plugin descriptor for the Standard Catalog plugin.

System, Component, Resource, Team, and Actor live here — Atlas Core itself
registers no concrete Entity Kind (plugin-architecture.md's core boundary).
This plugin is required in the official distribution: `SELECTED_PLUGINS`
omitting it fails composition (`server.apps.plugins.composition`).
"""

from atlas_plugin_api import PluginDescriptor, bind_actor_provisioning_service

PLUGIN = PluginDescriptor(
    id="atlas.standard-catalog",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("atlas_plugin_standard_catalog",),
    entry_point="atlas_plugin_standard_catalog.plugin:PLUGIN",
)


def register_runtime() -> None:
    """Populate this plugin's runtime registrations.

    Called by the shared "load selected runtime entry points" phase
    (`server.apps.plugins.runtime.load_runtime_entry_points`), after
    `django.setup()` — never at import time.
    """
    from atlas_plugin_standard_catalog.actor_provisioning import (
        actor_provisioning_service,
    )
    from atlas_plugin_standard_catalog.kinds import (
        register_standard_catalog_kinds,
    )

    register_standard_catalog_kinds(owner=PLUGIN.id)
    bind_actor_provisioning_service(actor_provisioning_service, owner=PLUGIN.id)
