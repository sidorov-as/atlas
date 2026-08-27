"""Static descriptor and runtime registration for the fixture provider."""

from atlas_plugin_api import (
    AuthenticationFlowKind,
    AuthenticationProviderContribution,
    AuthenticationProviderDescriptor,
    AuthenticationProviderPresentation,
    CredentialFieldKind,
    CredentialFieldPresentation,
    PluginDescriptor,
)

from .config import FixtureCredentialConfig

PROVIDER_ID = "example.auth.fixture"

PROVIDER_DESCRIPTOR = AuthenticationProviderDescriptor(
    id=PROVIDER_ID,
    flow_kind=AuthenticationFlowKind.CREDENTIALS,
    presentation=AuthenticationProviderPresentation(
        display_name="Development fixture credentials",
        credential_fields=(
            CredentialFieldPresentation(
                id="username",
                label="Fixture username",
                kind=CredentialFieldKind.TEXT,
                autocomplete="username",
            ),
            CredentialFieldPresentation(
                id="password",
                label="Fixture password",
                kind=CredentialFieldKind.SECRET,
                autocomplete="current-password",
            ),
        ),
    ),
)

PLUGIN = PluginDescriptor(
    id=PROVIDER_ID,
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1", "pluginApi": ">=0.1 <1"},
    django_apps=(),
    entry_point="atlas_example_auth_fixture.plugin:PLUGIN",
    config_schema=FixtureCredentialConfig,
    authentication_providers=(
        AuthenticationProviderContribution(
            descriptor=PROVIDER_DESCRIPTOR,
            config_schema=FixtureCredentialConfig,
            source_id_config_field="source_id",
            supported_group_sync_modes=("exact",),
        ),
    ),
)


def register_runtime() -> None:
    from atlas_plugin_api import register_authentication_provider

    from .provider import FixtureCredentialProvider, configured_fixture

    register_authentication_provider(
        FixtureCredentialProvider(configured_fixture()), owner=PLUGIN.id
    )
