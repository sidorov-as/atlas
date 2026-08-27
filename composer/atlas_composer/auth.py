"""Static authentication-provider metadata known to the composer."""

from collections.abc import Mapping

from atlas_plugin_api import (
    AuthenticationFlowKind,
    AuthenticationProviderContribution,
    AuthenticationProviderDescriptor,
    AuthenticationProviderPresentation,
    CredentialFieldKind,
    CredentialFieldPresentation,
    PluginDescriptor,
)

LOCAL_PROVIDER_ID = "atlas.auth.local"
LOCAL_PROVIDER_OWNER = "atlas.catalog"

LOCAL_AUTHENTICATION_PROVIDER = AuthenticationProviderContribution(
    descriptor=AuthenticationProviderDescriptor(
        id=LOCAL_PROVIDER_ID,
        flow_kind=AuthenticationFlowKind.CREDENTIALS,
        presentation=AuthenticationProviderPresentation(
            display_name="Username and password",
            credential_fields=(
                CredentialFieldPresentation(
                    id="username",
                    label="Username",
                    kind=CredentialFieldKind.TEXT,
                    autocomplete="username",
                ),
                CredentialFieldPresentation(
                    id="password",
                    label="Password",
                    kind=CredentialFieldKind.SECRET,
                    autocomplete="current-password",
                ),
            ),
        ),
    ),
    supported_group_sync_modes=("none",),
)


def authentication_provider_contributions(
    descriptors: Mapping[str, PluginDescriptor],
) -> dict[str, tuple[str, AuthenticationProviderContribution]]:
    """Return provider id -> (owning component id, static contribution)."""

    providers = {
        LOCAL_PROVIDER_ID: (LOCAL_PROVIDER_OWNER, LOCAL_AUTHENTICATION_PROVIDER),
    }
    for owner, plugin in descriptors.items():
        for contribution in plugin.authentication_providers:
            providers[contribution.descriptor.id] = (owner, contribution)
    return providers
