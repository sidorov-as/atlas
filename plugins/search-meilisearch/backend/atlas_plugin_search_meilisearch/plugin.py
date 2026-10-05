"""Static plugin descriptor for the Meilisearch search engine adapter.

Keeps the search index in a Meilisearch instance, which the plugin declares as
a required service: the composer runs it next to the application and wires its
address and access key into this plugin's configuration, or points the plugin
at an instance the operator already runs. It only registers an engine; select
it instead of the PostgreSQL adapter by naming this plugin in the manifest.
"""

from atlas_plugin_api import PluginDescriptor, RequiredService

from .config import SearchMeilisearchPluginConfig

MEILISEARCH_SERVICE = RequiredService(
    id="meilisearch",
    purpose="Search index for the Meilisearch engine adapter",
    image="getmeili/meilisearch:v1.12",
    port=7700,
    health_check=("curl", "-fsS", "http://localhost:7700/health"),
    config_keys={"address": "url", "secret": "key"},
    secret_env="MEILI_MASTER_KEY",
    data_path="/meili_data",
)

PLUGIN = PluginDescriptor(
    id="atlas.search-meilisearch",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=(),
    entry_point="atlas_plugin_search_meilisearch.plugin:PLUGIN",
    config_schema=SearchMeilisearchPluginConfig,
    required_services=(MEILISEARCH_SERVICE,),
)


def register_runtime() -> None:
    from atlas_plugin_api import get_plugin_config, register_search_engine

    from .engine import MeilisearchSearchEngine

    config = get_plugin_config(PLUGIN.id, SearchMeilisearchPluginConfig)
    register_search_engine(MeilisearchSearchEngine(config), owner=PLUGIN.id)
