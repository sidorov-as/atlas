"""Static descriptor and runtime registration for ``atlas.auth.oidc``."""

from atlas_plugin_api import (
    AuthenticationFlowKind,
    AuthenticationProviderContribution,
    AuthenticationProviderDescriptor,
    AuthenticationProviderPresentation,
    PluginDescriptor,
    RemoteLogoutCapability,
)

from .config import OIDCConfig

PROVIDER_ID = "atlas.auth.oidc"

PROVIDER_DESCRIPTOR = AuthenticationProviderDescriptor(
    id=PROVIDER_ID,
    flow_kind=AuthenticationFlowKind.REDIRECT,
    presentation=AuthenticationProviderPresentation(
        display_name="Single sign-on (OIDC)"
    ),
    remote_logout=RemoteLogoutCapability.SUPPORTED,
)

PLUGIN = PluginDescriptor(
    id=PROVIDER_ID,
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1", "pluginApi": ">=0.1 <1"},
    django_apps=("atlas_plugin_auth_oidc",),
    entry_point="atlas_plugin_auth_oidc.plugin:PLUGIN",
    config_schema=OIDCConfig,
    authentication_providers=(
        AuthenticationProviderContribution(
            descriptor=PROVIDER_DESCRIPTOR,
            config_schema=OIDCConfig,
            django_apps=("atlas_plugin_auth_oidc",),
            source_id_config_field="expected_issuer",
        ),
    ),
)


def register_runtime() -> None:
    from atlas_plugin_api import register_authentication_provider

    from .provider import OIDCProvider, configured_oidc

    register_authentication_provider(
        OIDCProvider(configured_oidc()), owner=PLUGIN.id
    )
