"""Typed configuration for `atlas.search-postgres`.

Free of Django imports: `PLUGIN.config_schema` is evaluated during the static
plugin-descriptor phase, before `django.setup()` runs.
"""

from atlas_plugin_api import PluginConfigSchema
from pydantic import Field

DEFAULT_TEXT_SEARCH_CONFIG = "simple"


class SearchPostgresPluginConfig(PluginConfigSchema):
    """`atlas.search-postgres` plugin configuration; every field is optional."""

    text_search_config: str = Field(
        default=DEFAULT_TEXT_SEARCH_CONFIG,
        alias="textSearchConfig",
        pattern=r"^[a-z_][a-z0-9_]*$",
    )
    """PostgreSQL text-search configuration used to build and query the
    vectors (for example `english` or `russian`). `simple` does no stemming and
    no stop-word removal, so it behaves the same for every language. Vectors
    are built when a document is indexed: after changing this setting run the
    search plugin's reindex command to rebuild them."""
