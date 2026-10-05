"""Typed configuration for `atlas.search-meilisearch`.

Free of Django imports: `PLUGIN.config_schema` is evaluated during the static
plugin-descriptor phase, before `django.setup()` runs.
"""

from urllib.parse import urlsplit

from atlas_plugin_api import PluginConfigSchema, SecretRef
from pydantic import Field, field_validator

DEFAULT_INDEX = "atlas-search"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0
DEFAULT_TASK_TIMEOUT_SECONDS = 60.0


class SearchMeilisearchPluginConfig(PluginConfigSchema):
    """`atlas.search-meilisearch` plugin configuration.

    `url` and `key` are normally filled in by the composer from the service
    the plugin declares; an operator may set either explicitly.
    """

    url: str
    """Base URL of the Meilisearch instance. Operator-supplied, never user
    input: the adapter connects to it directly and to nothing else."""

    key: str | SecretRef | None = None
    """Access key used for indexing and searching. Optional only for an
    instance that enforces none."""

    index: str = Field(
        default=DEFAULT_INDEX,
        pattern=r"^[A-Za-z0-9_-]{1,100}$",
    )
    """Index uid holding the documents."""

    request_timeout_seconds: float = Field(
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        alias="requestTimeoutSeconds",
        gt=0,
    )
    """Timeout of a single HTTP request."""

    task_timeout_seconds: float = Field(
        default=DEFAULT_TASK_TIMEOUT_SECONDS,
        alias="taskTimeoutSeconds",
        gt=0,
    )
    """How long a write waits for the engine to finish applying it. A write
    that does not finish in time is reported as failed."""

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("url must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("url must not carry credentials, a query or a fragment")
        return value.rstrip("/")
