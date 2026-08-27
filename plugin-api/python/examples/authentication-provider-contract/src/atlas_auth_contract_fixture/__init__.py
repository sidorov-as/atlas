"""Minimal separately packaged credential provider used by contract tests."""

from atlas_plugin_api import (
    AuthenticationFailure,
    AuthenticationFailureCategory,
    AuthenticationFlowKind,
    AuthenticationProviderDescriptor,
    AuthenticationProviderPresentation,
    CredentialFieldKind,
    CredentialFieldPresentation,
    ExternalGroupSnapshot,
    ExternalProfile,
    VerifiedIdentity,
)

PROVIDER_ID = "example.auth.out-of-tree"
SOURCE_ID = "urn:atlas:fixture-directory"


class FixtureCredentialProvider:
    descriptor = AuthenticationProviderDescriptor(
        id=PROVIDER_ID,
        flow_kind=AuthenticationFlowKind.CREDENTIALS,
        presentation=AuthenticationProviderPresentation(
            display_name="Out-of-tree fixture",
            credential_fields=(
                CredentialFieldPresentation(
                    id="username",
                    label="Username",
                    kind=CredentialFieldKind.TEXT,
                ),
                CredentialFieldPresentation(
                    id="password",
                    label="Password",
                    kind=CredentialFieldKind.SECRET,
                ),
            ),
        ),
    )

    def authenticate(self, context, credentials):
        username = credentials.values["username"]
        if username == "unavailable":
            return AuthenticationFailure(
                AuthenticationFailureCategory.UNAVAILABLE, retryable=True
            )
        if credentials.values != {"username": "person", "password": "fixture"}:
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_CREDENTIALS
            )
        return VerifiedIdentity(
            provider_id=PROVIDER_ID,
            source_id=SOURCE_ID,
            subject="fixture-person-1",
            profile=ExternalProfile(username="person"),
            groups=ExternalGroupSnapshot.complete(),
        )


__all__ = ["PROVIDER_ID", "SOURCE_ID", "FixtureCredentialProvider"]
