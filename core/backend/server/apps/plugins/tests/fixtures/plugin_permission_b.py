"""Fixture plugin registering the same permission id as `plugin_permission_a`,
for composition-validation tests."""

from server.apps.plugins import PluginDescriptor
from server.apps.plugins.permissions import registry as permission_registry

PLUGIN = PluginDescriptor(
    id="fixture.permission-b",
    version="0.0.0",
    compatibility={},
    django_apps=(),
    entry_point="server.apps.plugins.tests.fixtures.plugin_permission_b:PLUGIN",
)


def register_runtime() -> None:
    permission_registry.register("fixture.shared.permission", owner=PLUGIN.id)
