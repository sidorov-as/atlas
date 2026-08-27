"""Fixture plugin declaring a manifest dependency nothing selected satisfies
(used by the composition tests)."""

from server.apps.plugins import PluginDescriptor

PLUGIN = PluginDescriptor(
    id="fixture.needs-missing",
    version="0.0.0",
    compatibility={},
    django_apps=(),
    entry_point="server.apps.plugins.tests.fixtures.plugin_missing_dependency:PLUGIN",
    requires_plugins={"fixture.does-not-exist": ">=1 <2"},
)
