"""Required service declaration tests (deployment-required-services spec)."""

import pytest

from atlas_plugin_api import PluginDescriptor, RequiredService


def _service(**overrides) -> RequiredService:
    fields = {
        "id": "meilisearch",
        "purpose": "Search index",
        "image": "getmeili/meilisearch:v1.12",
        "port": 7700,
        "health_check": ("curl", "-f", "http://localhost:7700/health"),
        "config_keys": {"address": "url", "secret": "api_key"},
        "secret_env": "MEILI_MASTER_KEY",
        "data_path": "/meili_data",
    }
    fields.update(overrides)
    return RequiredService(**fields)


def test_a_descriptor_defaults_to_no_required_services():
    descriptor = PluginDescriptor(
        id="atlas.x",
        version="0.1.0",
        compatibility={},
        django_apps=(),
        entry_point="x:PLUGIN",
    )
    assert descriptor.required_services == ()


@pytest.mark.parametrize(
    "image", ["getmeili/meilisearch", "getmeili/meilisearch:latest", "host:5000/img"]
)
def test_an_unpinned_image_is_rejected(image):
    with pytest.raises(ValueError, match="pinned"):
        _service(image=image)


@pytest.mark.parametrize(
    "image",
    ["getmeili/meilisearch:v1.12", "host:5000/img:1.0", "img@sha256:" + "a" * 64],
)
def test_a_tag_or_digest_is_pinned(image):
    assert _service(image=image).image == image


def test_service_id_must_be_a_compose_safe_name():
    with pytest.raises(ValueError, match="service id"):
        _service(id="Meili_Search")


def test_config_keys_require_an_address():
    with pytest.raises(ValueError, match="config_keys"):
        _service(config_keys={"secret": "api_key"})


def test_secret_key_and_secret_env_go_together():
    with pytest.raises(ValueError, match="secret_env"):
        _service(secret_env=None)
    with pytest.raises(ValueError, match="secret_env"):
        _service(config_keys={"address": "url"})


def test_data_path_must_be_absolute():
    with pytest.raises(ValueError, match="absolute"):
        _service(data_path="meili_data")


def test_a_descriptor_rejects_duplicate_service_ids():
    with pytest.raises(ValueError, match="duplicate service ids"):
        PluginDescriptor(
            id="atlas.x",
            version="0.1.0",
            compatibility={},
            django_apps=(),
            entry_point="x:PLUGIN",
            required_services=(_service(), _service()),
        )
