"""Fixture plugin with no runtime hook (mirrors
`server.apps.catalog.plugin`)."""

from server.apps.plugins import PluginDescriptor

PLUGIN = PluginDescriptor(
    id="fixture.no-hook",
    version="0.0.0",
    compatibility={},
    django_apps=(),
    entry_point="server.apps.plugins.tests.fixtures.plugin_no_hook:PLUGIN",
)
