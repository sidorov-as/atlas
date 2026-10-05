import pytest
from atlas_plugin_api import bind_plugin_config, select_search_engine
from atlas_plugin_api import config as plugin_config
from atlas_plugin_api import search as search_contract

from atlas_plugin_search_meilisearch import plugin
from atlas_plugin_search_meilisearch.config import SearchMeilisearchPluginConfig
from atlas_plugin_search_meilisearch.engine import MeilisearchSearchEngine


@pytest.fixture(autouse=True)
def clean_state():
    search_contract._search_engine_registry.__init__()
    plugin_config._resolved_plugin_configs.pop(plugin.PLUGIN.id, None)
    yield
    search_contract._search_engine_registry.__init__()
    plugin_config._resolved_plugin_configs.pop(plugin.PLUGIN.id, None)


def test_descriptor():
    assert plugin.PLUGIN.id == "atlas.search-meilisearch"
    assert plugin.PLUGIN.django_apps == ()
    assert [s.id for s in plugin.PLUGIN.required_services] == ["meilisearch"]


def test_register_runtime_registers_the_engine_owned_by_the_plugin():
    bind_plugin_config(
        plugin.PLUGIN.id,
        SearchMeilisearchPluginConfig(url="http://meili:7700"),
        owner=plugin.PLUGIN.id,
    )
    plugin.register_runtime()

    lookup = search_contract.get_search_engine_lookup()
    (engine,) = lookup.all()
    assert isinstance(engine, MeilisearchSearchEngine)
    assert lookup.owner_of(engine.id) == plugin.PLUGIN.id
    assert select_search_engine(lookup, plugin.PLUGIN.id) is engine


def test_startup_without_configuration_fails():
    with pytest.raises(LookupError):
        plugin.register_runtime()
