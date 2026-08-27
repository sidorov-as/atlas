"""Typed private configuration for the development fixture provider."""

from atlas_plugin_api import PluginConfigSchema, SecretRef
from pydantic import Field, field_validator


class FixtureCredentialConfig(PluginConfigSchema):
    development_enabled: bool = Field(alias="developmentEnabled")
    source_id: str = Field(alias="sourceId", min_length=1)
    fixture_password: str | SecretRef = Field(alias="fixturePassword")

    @field_validator("development_enabled")
    @classmethod
    def require_development_opt_in(cls, value: bool) -> bool:
        if not value:
            raise ValueError(
                "the fixture provider requires developmentEnabled=true"
            )
        return value

    @field_validator("source_id")
    @classmethod
    def require_fixture_namespace(cls, value: str) -> str:
        if not value.startswith("urn:atlas:directory:fixture-"):
            raise ValueError(
                "sourceId must use a fixture-only Atlas directory namespace"
            )
        return value
