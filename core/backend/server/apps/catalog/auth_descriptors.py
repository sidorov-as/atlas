"""Django-free static descriptors for Core-owned authentication providers."""

from atlas_plugin_api import (
    AuthenticationFlowKind,
    AuthenticationProviderDescriptor,
    AuthenticationProviderPresentation,
    CredentialFieldKind,
    CredentialFieldPresentation,
)

LOCAL_PROVIDER_ID = "atlas.auth.local"
LOCAL_SOURCE_ID = "urn:atlas:local"

LOCAL_PROVIDER_DESCRIPTOR = AuthenticationProviderDescriptor(
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
)
