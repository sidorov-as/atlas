"""Fixture plugin with a runtime hook, recording that it ran."""

from server.apps.plugins import PluginDescriptor

PLUGIN = PluginDescriptor(
    id="fixture.with-hook",
    version="0.0.0",
    compatibility={},
    django_apps=(),
    entry_point="server.apps.plugins.tests.fixtures.plugin_with_hook:PLUGIN",
)

runtime_calls: list[str] = []


def register_runtime() -> None:
    runtime_calls.append(PLUGIN.id)
