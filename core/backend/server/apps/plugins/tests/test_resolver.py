"""Selected-plugin resolver tests (plugin-registries spec)."""

import pytest

from server.apps.plugins import (
    MissingPluginDescriptorError,
    PluginDescriptor,
    load_selected_descriptors,
    resolve_installed_apps,
)


def test_load_selected_descriptors_imports_each_module_path():
    descriptors = load_selected_descriptors(
        (
            "server.apps.catalog.plugin",
            "atlas_plugin_ingestion.plugin",
        )
    )

    assert [descriptor.id for descriptor in descriptors] == [
        "atlas.catalog",
        "atlas.ingestion",
    ]


def test_load_selected_descriptors_rejects_a_module_without_plugin():
    with pytest.raises(MissingPluginDescriptorError) as exc_info:
        load_selected_descriptors(("server.apps.catalog",))

    assert "server.apps.catalog" in str(exc_info.value)


def test_resolve_installed_apps_flattens_selected_django_apps_then_additional():
    descriptors = (
        PluginDescriptor(
            id="atlas.a",
            version="0.1.0",
            compatibility={},
            django_apps=("a.one", "a.two"),
            entry_point="a.plugin:PLUGIN",
        ),
        PluginDescriptor(
            id="atlas.b",
            version="0.1.0",
            compatibility={},
            django_apps=("b.one",),
            entry_point="b.plugin:PLUGIN",
        ),
    )

    installed_apps = resolve_installed_apps(
        descriptors,
        additional_apps=("django.contrib.admin",),
    )

    assert installed_apps == ("a.one", "a.two", "b.one", "django.contrib.admin")


def test_an_unselected_plugin_contributes_nothing():
    # Only descriptors actually passed in are reflected — an
    # importable-but-unselected plugin's apps never appear.
    installed_apps = resolve_installed_apps(
        (),
        additional_apps=("django.contrib.admin",),
    )

    assert installed_apps == ("django.contrib.admin",)
