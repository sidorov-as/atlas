"""Central plugin configuration registry tests
(`plugin-configuration-isolation` spec)."""

import pytest
from atlas_plugin_api import PluginConfigSchema, SecretRef
from atlas_plugin_api.config import MissingSecretEnvError

from server.apps.plugins.config import PluginConfigRegistry


class _OIDCConfig(PluginConfigSchema):
    issuer: str
    client_secret: str | SecretRef

    PUBLIC_FIELDS = frozenset({"issuer"})


def test_register_resolves_a_fromenv_secret(monkeypatch):
    monkeypatch.setenv("ATLAS_OIDC_CLIENT_SECRET", "sekret-value")
    registry = PluginConfigRegistry()

    resolved = registry.register(
        "atlas.auth.oidc",
        _OIDCConfig,
        {
            "issuer": "https://id.example.com",
            "client_secret": {"fromEnv": "ATLAS_OIDC_CLIENT_SECRET"},
        },
    )

    assert resolved.client_secret == "sekret-value"
    assert registry.get("atlas.auth.oidc") is resolved


def test_register_raises_when_the_referenced_env_var_is_unset(monkeypatch):
    monkeypatch.delenv("ATLAS_OIDC_CLIENT_SECRET", raising=False)
    registry = PluginConfigRegistry()

    with pytest.raises(MissingSecretEnvError):
        registry.register(
            "atlas.auth.oidc",
            _OIDCConfig,
            {
                "issuer": "https://id.example.com",
                "client_secret": {"fromEnv": "ATLAS_OIDC_CLIENT_SECRET"},
            },
        )


def test_get_returns_none_for_an_unregistered_plugin():
    registry = PluginConfigRegistry()

    assert registry.get("atlas.auth.oidc") is None


def test_public_bootstrap_config_includes_only_declared_public_fields():
    registry = PluginConfigRegistry()
    registry.register(
        "atlas.auth.oidc",
        _OIDCConfig,
        {
            "issuer": "https://id.example.com",
            "client_secret": "sekret-value",
        },
    )

    assert registry.public_bootstrap_config() == {
        "atlas.auth.oidc": {"issuer": "https://id.example.com"},
    }


def test_public_bootstrap_config_never_contains_a_secret_value():
    registry = PluginConfigRegistry()
    registry.register(
        "atlas.auth.oidc",
        _OIDCConfig,
        {
            "issuer": "https://id.example.com",
            "client_secret": "sekret-value-do-not-leak",
        },
    )

    bootstrap_config = registry.public_bootstrap_config()

    assert "sekret-value-do-not-leak" not in repr(bootstrap_config)
