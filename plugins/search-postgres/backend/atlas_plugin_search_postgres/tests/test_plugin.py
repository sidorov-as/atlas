import pytest
from atlas_plugin_api import search as search_contract
from atlas_plugin_api import select_search_engine

from atlas_plugin_search_postgres import plugin
from atlas_plugin_search_postgres.config import SearchPostgresPluginConfig
from atlas_plugin_search_postgres.engine import PostgresSearchEngine


@pytest.fixture(autouse=True)
def clean_registry():
    search_contract._search_engine_registry.__init__()
    yield
    search_contract._search_engine_registry.__init__()


def test_descriptor():
    assert plugin.PLUGIN.id == "atlas.search-postgres"
    assert plugin.PLUGIN.django_apps == ("atlas_plugin_search_postgres",)
    assert plugin.PLUGIN.config_schema is SearchPostgresPluginConfig


def test_config_defaults_and_validation():
    assert SearchPostgresPluginConfig().text_search_config == "simple"
    assert (
        SearchPostgresPluginConfig(textSearchConfig="english").text_search_config
        == "english"
    )
    with pytest.raises(ValueError):
        SearchPostgresPluginConfig(textSearchConfig="english; drop")


def test_register_runtime_registers_the_engine_owned_by_the_plugin():
    plugin.register_runtime()

    lookup = search_contract.get_search_engine_lookup()
    (engine,) = lookup.all()
    assert isinstance(engine, PostgresSearchEngine)
    assert lookup.owner_of(engine.id) == plugin.PLUGIN.id
    assert select_search_engine(lookup, plugin.PLUGIN.id) is engine
    assert select_search_engine(lookup) is engine
