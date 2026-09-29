"""Typed configuration for ``atlas.c4``: which PlantUML backend renders diagrams.

Kept free of Django imports: ``PLUGIN.config_schema`` is evaluated during the
static plugin-descriptor phase, before ``django.setup()`` runs.
"""

from typing import Literal
from urllib.parse import urlsplit

from atlas_plugin_api import PluginConfigSchema
from pydantic import Field, model_validator

DEFAULT_TIMEOUT_SECONDS = 30.0


class C4PluginConfig(PluginConfigSchema):
    """``renderer: local`` runs the bundled PlantUML executable (default).

    ``renderer: remote`` sends the diagram source to a PlantUML server, which
    avoids the JVM in memory-constrained deployments. ``serverUrl`` defaults to
    c4-diagrams' public server; point it at a self-hosted one for private
    catalogs, since the diagram text leaves the deployment.
    """

    renderer: Literal["local", "remote"] = "local"
    server_url: str | None = Field(default=None, alias="serverUrl")
    timeout_seconds: float = Field(
        default=DEFAULT_TIMEOUT_SECONDS, alias="timeoutSeconds", gt=0, le=300
    )

    @model_validator(mode="after")
    def validate_renderer_options(self) -> "C4PluginConfig":
        if self.server_url is None:
            return self
        if self.renderer != "remote":
            raise ValueError("serverUrl is only valid with renderer: remote")
        parsed = urlsplit(self.server_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("serverUrl must be an http(s) URL without credentials")
        return self
