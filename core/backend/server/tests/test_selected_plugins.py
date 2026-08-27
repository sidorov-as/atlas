"""Deployment plugin-selection tests (plugin-registries spec)."""

from server.settings.selected_plugins import SELECTED_PLUGINS


def test_selected_plugins_lists_the_in_tree_apps():
    assert SELECTED_PLUGINS == (
        "server.apps.catalog.plugin",
        "atlas_plugin_standard_catalog.plugin",
        "atlas_plugin_apis.plugin",
        "atlas_plugin_c4.plugin",
        "atlas_plugin_database_schema.plugin",
        "atlas_plugin_ingestion.plugin",
        "atlas_plugin_flows.plugin",
    )
