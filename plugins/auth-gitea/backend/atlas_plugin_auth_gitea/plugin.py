"""Static descriptor and runtime registration for ``atlas.auth.gitea``."""

from atlas_plugin_api import (
    AuthenticationFlowKind,
    AuthenticationProviderContribution,
    AuthenticationProviderDescriptor,
    AuthenticationProviderPresentation,
    PluginDescriptor,
    RemoteLogoutCapability,
)

from .config import GiteaConfig

PROVIDER_ID = "atlas.auth.gitea"
SUPPORTED_GITEA_VERSION = "1.27.3"
SUPPORTED_ALLAUTH_VERSION = "65.19.1"

PROVIDER_DESCRIPTOR = AuthenticationProviderDescriptor(
    id=PROVIDER_ID,
    flow_kind=AuthenticationFlowKind.REDIRECT,
    presentation=AuthenticationProviderPresentation(display_name="Gitea"),
    remote_logout=RemoteLogoutCapability.UNSUPPORTED,
)

PLUGIN = PluginDescriptor(
    id=PROVIDER_ID,
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1", "pluginApi": ">=0.1 <1"},
    django_apps=("atlas_plugin_auth_gitea",),
    entry_point="atlas_plugin_auth_gitea.plugin:PLUGIN",
    config_schema=GiteaConfig,
    authentication_providers=(
        AuthenticationProviderContribution(
            descriptor=PROVIDER_DESCRIPTOR,
            config_schema=GiteaConfig,
            django_apps=("atlas_plugin_auth_gitea",),
            source_id_config_field="instance_origin",
            supported_group_sync_modes=("none",),
        ),
    ),
)


def register_runtime() -> None:
    from atlas_plugin_api import register_authentication_provider

    from .provider import GiteaProvider, configured_gitea

    register_authentication_provider(
        GiteaProvider(configured_gitea()), owner=PLUGIN.id
    )
