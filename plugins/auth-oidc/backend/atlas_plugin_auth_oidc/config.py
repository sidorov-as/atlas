"""Typed, private configuration for ``atlas.auth.oidc``."""

from urllib.parse import urlsplit

from atlas_plugin_api import PluginConfigSchema, SecretRef
from pydantic import Field, field_validator


def _is_loopback_hostname(hostname: str | None) -> bool:
    return hostname in {"localhost", "127.0.0.1", "::1"} or bool(
        hostname and hostname.endswith(".localhost")
    )


class OIDCConfig(PluginConfigSchema):
    discovery_url: str = Field(alias="discoveryUrl")
    expected_issuer: str = Field(alias="expectedIssuer")
    client_id: str = Field(alias="clientId")
    client_secret: str | SecretRef = Field(alias="clientSecret")
    scopes: tuple[str, ...] = ("openid", "profile", "email")
    groups_claim: str | None = Field(default="groups", alias="groupsClaim")
    allowed_algorithms: tuple[str, ...] = Field(
        default=("RS256",), alias="allowedAlgorithms"
    )
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
    remote_logout: bool = Field(default=False, alias="remoteLogout")

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

    @field_validator("scopes")
    @classmethod
    def require_openid_scope(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if "openid" not in value:
            raise ValueError("OIDC scopes must include 'openid'")
        if len(value) != len(set(value)):
            raise ValueError("OIDC scopes must be unique")
        return value

    @field_validator("allowed_algorithms")
    @classmethod
    def reject_symmetric_algorithms(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        if not value or any(
            item.startswith("HS") or item == "none" for item in value
        ):
            raise ValueError("OIDC algorithms must be asymmetric and explicit")
        return value
