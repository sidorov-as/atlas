"""Selected-descriptor verification tests (plugin-registries spec)."""

import pytest
from atlas_plugin_api import PluginDescriptor

from server.apps.plugins.resolver import (
    DuplicatePluginIdError,
    InvalidPluginDescriptorError,
    verify_selected_descriptors,
)


def _descriptor(**overrides):
    fields = {
        "id": "atlas.a",
        "version": "0.1.0",
        "compatibility": {},
        "django_apps": (),
        "entry_point": "a.plugin:PLUGIN",
    }
    fields.update(overrides)
    return PluginDescriptor(**fields)


def test_verify_passes_for_distinct_well_formed_descriptors():
    descriptors = (_descriptor(id="atlas.a"), _descriptor(id="atlas.b"))

    verify_selected_descriptors(descriptors)  # must not raise


def test_verify_rejects_two_selected_plugins_sharing_an_id():
    descriptors = (_descriptor(id="atlas.a"), _descriptor(id="atlas.a"))

    with pytest.raises(DuplicatePluginIdError) as exc_info:
        verify_selected_descriptors(descriptors)

    assert exc_info.value.plugin_id == "atlas.a"


def test_verify_rejects_a_descriptor_with_an_empty_id():
    descriptors = (_descriptor(id=""),)

    with pytest.raises(InvalidPluginDescriptorError):
        verify_selected_descriptors(descriptors)


def test_verify_rejects_a_descriptor_with_an_empty_version():
    descriptors = (_descriptor(version=""),)

    with pytest.raises(InvalidPluginDescriptorError):
        verify_selected_descriptors(descriptors)
