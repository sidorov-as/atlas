import pytest
from atlas_plugin_api import SecretRef, resolve_secrets
from pydantic import ValidationError

from atlas_plugin_search_meilisearch import plugin
from atlas_plugin_search_meilisearch.config import SearchMeilisearchPluginConfig


def test_defaults():
    config = SearchMeilisearchPluginConfig(url="http://meili:7700/")
    assert config.url == "http://meili:7700"
    assert config.key is None
    assert config.index == "atlas-search"
    assert config.task_timeout_seconds > 0


@pytest.mark.parametrize(
    "url",
    ["meili:7700", "ftp://meili", "http://u:p@meili", "http://meili?a=1", ""],
)
def test_url_must_be_a_plain_http_origin(url):
    with pytest.raises(ValidationError):
        SearchMeilisearchPluginConfig(url=url)


def test_url_is_required():
    with pytest.raises(ValidationError):
        SearchMeilisearchPluginConfig()


def test_index_uid_is_restricted_to_the_engine_charset():
    with pytest.raises(ValidationError):
        SearchMeilisearchPluginConfig(url="http://m", index="a/b")


def test_key_is_a_secret_reference_that_never_shows_in_repr_or_dump():
    config = SearchMeilisearchPluginConfig(url="http://m", key={"fromEnv": "MEILI_KEY"})
    assert isinstance(config.key, SecretRef)

    resolved = resolve_secrets(config, env={"MEILI_KEY": "s3cret"})
    assert resolved.key == "s3cret"
    assert "s3cret" not in repr(resolved)
    assert "s3cret" not in str(resolved.redacted_dump())


def test_public_projection_contains_no_key():
    config = SearchMeilisearchPluginConfig(url="http://m", key="s3cret")
    assert config.public_projection() == {}


def test_descriptor_declares_the_service_and_wires_it_to_real_fields():
    (service,) = plugin.PLUGIN.required_services
    fields = set(SearchMeilisearchPluginConfig.model_fields)
    assert {service.config_keys["address"], service.config_keys["secret"]} <= fields
    assert plugin.PLUGIN.config_schema is SearchMeilisearchPluginConfig
