"""Typed, private configuration for ``atlas.auth.gitea``."""

from urllib.parse import urlsplit

from atlas_plugin_api import PluginConfigSchema, SecretRef
from pydantic import Field, field_validator, model_validator


def _is_loopback_hostname(hostname: str | None) -> bool:
    return hostname in {"localhost", "127.0.0.1", "::1"} or bool(
        hostname and hostname.endswith(".localhost")
    )


class GiteaConfig(PluginConfigSchema):
    instance_origin: str = Field(alias="instanceOrigin")
    client_id: str = Field(alias="clientId", min_length=1)
    client_secret: str | SecretRef = Field(alias="clientSecret")
    scopes: tuple[str, ...] = ("read:user",)
    oauth_pkce_enabled: bool = Field(default=True, alias="oauthPkceEnabled")
    connect_timeout_seconds: float = Field(
        default=3.0, alias="connectTimeoutSeconds", gt=0, le=30
    )
    read_timeout_seconds: float = Field(
        default=5.0, alias="readTimeoutSeconds", gt=0, le=60
    )
    max_response_bytes: int = Field(
        default=1_048_576, alias="maxResponseBytes", gt=0, le=4_194_304
    )
    allowed_destinations: tuple[str, ...] = Field(
        default=(), alias="allowedDestinations"
    )
    allow_development_http: bool = Field(
        default=False, alias="allowDevelopmentHttp"
    )

    @field_validator("allowed_destinations")
    @classmethod
    def validate_allowed_destinations(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"https", "http"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or parsed.path not in {"", "/"}
            ):
                raise ValueError("allowedDestinations must contain origins")
            if parsed.scheme == "http" and not _is_loopback_hostname(
                parsed.hostname
            ):
                raise ValueError(
                    "plaintext allowedDestinations are limited to loopback"
                )
        return tuple(item.rstrip("/") for item in values)

    @field_validator("instance_origin")
    @classmethod
    def normalize_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError(
                "instanceOrigin must contain only scheme and authority"
            )
        return value.rstrip("/")

    @field_validator("scopes")
    @classmethod
    def require_minimal_scope(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != ("read:user",):
            raise ValueError("Gitea v1 requires exactly the 'read:user' scope")
        return value

    @field_validator("oauth_pkce_enabled")
    @classmethod
    def require_pkce(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Gitea v1 requires OAuth PKCE S256")
        return value

    @model_validator(mode="after")
    def reject_production_http(self) -> "GiteaConfig":
        if self.instance_origin.startswith("http://") and not (
            self.allow_development_http
            and _is_loopback_hostname(urlsplit(self.instance_origin).hostname)
        ):
            raise ValueError(
                "Gitea instanceOrigin must use HTTPS outside loopback "
                "development"
            )
        return self
