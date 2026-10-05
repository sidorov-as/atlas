"""Typed configuration for `atlas.search`.

Free of Django imports: `PLUGIN.config_schema` is evaluated during the static
plugin-descriptor phase, before `django.setup()` runs.
"""

from atlas_plugin_api import PluginConfigSchema
from pydantic import Field

DEFAULT_DRAIN_INTERVAL_SECONDS = 10
DEFAULT_REBUILD_INTERVAL_SECONDS = 6 * 60 * 60
DEFAULT_MIN_QUERY_LENGTH = 2


class SearchPluginConfig(PluginConfigSchema):
    """`atlas.search` plugin configuration; every field is optional."""

    engine: str | None = Field(default=None, min_length=1)
    """Plugin id of the engine adapter to use. Required only when several
    engine plugins are selected; composition checks that it is selected."""

    drain_interval_seconds: int = Field(
        default=DEFAULT_DRAIN_INTERVAL_SECONDS,
        alias="drainIntervalSeconds",
        gt=0,
    )
    rebuild_interval_seconds: int = Field(
        default=DEFAULT_REBUILD_INTERVAL_SECONDS,
        alias="rebuildIntervalSeconds",
        gt=0,
    )
    max_body_chars: int | None = Field(default=None, alias="maxBodyChars", gt=0)
    """Bound on an indexed document body; `None` keeps the contract default."""

    min_query_length: int = Field(
        default=DEFAULT_MIN_QUERY_LENGTH,
        alias="minQueryLength",
        gt=0,
    )
