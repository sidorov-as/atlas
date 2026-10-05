"""Static plugin descriptor for the PostgreSQL search engine adapter.

Keeps the search index in the application's own database, so it adds no
service to a deployment. It only registers an engine: with no search plugin
selected nothing uses it. The search plugin picks it at startup (or by its
`engine` setting naming this plugin id).
"""

from atlas_plugin_api import PluginDescriptor

from .config import SearchPostgresPluginConfig

PLUGIN = PluginDescriptor(
    id="atlas.search-postgres",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("atlas_plugin_search_postgres",),
    entry_point="atlas_plugin_search_postgres.plugin:PLUGIN",
    config_schema=SearchPostgresPluginConfig,
)


def register_runtime() -> None:
    from atlas_plugin_api import get_plugin_config, register_search_engine

    from .engine import PostgresSearchEngine

    try:
        config = get_plugin_config(PLUGIN.id, SearchPostgresPluginConfig)
    except LookupError:
        config = SearchPostgresPluginConfig()
    register_search_engine(
        PostgresSearchEngine(config.text_search_config), owner=PLUGIN.id
    )
