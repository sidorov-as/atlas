"""Fixture plugin registering a permission id, for composition tests."""

from server.apps.plugins import PluginDescriptor
from server.apps.plugins.permissions import registry as permission_registry

PLUGIN = PluginDescriptor(
    id="fixture.permission-a",
    version="0.0.0",
    compatibility={},
    django_apps=(),
    entry_point="server.apps.plugins.tests.fixtures.plugin_permission_a:PLUGIN",
)


def register_runtime() -> None:
    permission_registry.register("fixture.shared.permission", owner=PLUGIN.id)
