"""Tests import the descriptor taught by the first-plugin tutorial."""

import importlib.util
from pathlib import Path

PLUGIN_PATH = Path(__file__).parents[1] / "atlas_plugin_hello" / "plugin.py"


def load_plugin():
    spec = importlib.util.spec_from_file_location(
        "tutorial_plugin",
        PLUGIN_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PLUGIN


def test_descriptor_is_static_and_composable():
    plugin = load_plugin()

    assert plugin.id == "atlas.hello-atlas"
    assert plugin.version == "0.1.0"
    assert plugin.compatibility == {"atlasCore": ">=0.1 <1"}
    assert plugin.django_apps == ()
    assert plugin.entry_point == "atlas_plugin_hello.plugin:PLUGIN"
    assert plugin.requires_plugins == {}
