"""Static descriptor used by the first-plugin documentation tutorial."""

from atlas_plugin_api import PluginDescriptor

PLUGIN = PluginDescriptor(
    id="atlas.hello-atlas",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=(),
    entry_point="atlas_plugin_hello.plugin:PLUGIN",
)
