"""Contract tests for the public authentication-provider value surface."""

import dataclasses
from datetime import UTC, datetime, timedelta
from typing import assert_type

import pytest

import atlas_plugin_api.authentication as authentication_module
from atlas_plugin_api import (
    AUTHENTICATION_PROVIDER_CONTRACT_V1,
    AssuredAttribute,
    AttributeProvenance,
    AuthenticationFailure,
    AuthenticationFailureCategory,
    AuthenticationFlowKind,
    AuthenticationProvider,
    AuthenticationProviderDescriptor,
    AuthenticationProviderLookup,
    AuthenticationProviderPresentation,
    AuthenticationProviderRegistry,
    CredentialAuthenticationProvider,
    CredentialFieldKind,
    CredentialFieldPresentation,
    CredentialFlowContext,
    CredentialInput,
    DuplicateAuthenticationProviderError,
    ExternalGroupSnapshot,
    ExternalGroupSnapshotStatus,
    ExternalProfile,
    InvalidAuthenticationProviderError,
    InvalidAuthenticationResultError,
    RedirectAuthenticationProvider,
    RedirectCallbackContext,
    RedirectChallenge,
    RedirectFlowContext,
    RemoteLogoutCapability,
    VerifiedIdentity,
    get_authentication_provider_lookup,
    register_authentication_provider,
)


def _credential_descriptor(
    provider_id: str = "atlas.auth.fixture",
) -> AuthenticationProviderDescriptor:
    return AuthenticationProviderDescriptor(
        id=provider_id,
        flow_kind=AuthenticationFlowKind.CREDENTIALS,
        presentation=AuthenticationProviderPresentation(
            display_name="Fixture credentials",
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


def _redirect_descriptor(
    provider_id: str = "atlas.auth.redirect-fixture",
) -> AuthenticationProviderDescriptor:
    return AuthenticationProviderDescriptor(
        id=provider_id,
        flow_kind=AuthenticationFlowKind.REDIRECT,
        presentation=AuthenticationProviderPresentation(display_name="Fixture SSO"),
        remote_logout=RemoteLogoutCapability.SUPPORTED,
    )


def _flow_kwargs() -> dict[str, object]:
    return {
        "provider_id": "atlas.auth.fixture",
        "source_id": "urn:atlas:test-directory",
        "attempt_id": "attempt-1",
        "correlation_id": "correlation-1",
        "deadline": datetime.now(UTC) + timedelta(seconds=5),
    }


class _CredentialProvider:
    descriptor = _credential_descriptor()

    def authenticate(
        self,
        context: CredentialFlowContext,
        credentials: CredentialInput,
    ) -> AuthenticationFailure:
        return AuthenticationFailure(AuthenticationFailureCategory.INVALID_CREDENTIALS)


class _RedirectProvider:
    descriptor = _redirect_descriptor()

    def begin(self, context: RedirectFlowContext) -> RedirectChallenge:
        return RedirectChallenge("https://idp.example/authorize")

    def complete(self, context: RedirectCallbackContext) -> AuthenticationFailure:
        return AuthenticationFailure(AuthenticationFailureCategory.CANCELED)


def test_descriptor_exposes_versioned_static_presentation_metadata():
    descriptor = _credential_descriptor()

    assert descriptor.contract_version == AUTHENTICATION_PROVIDER_CONTRACT_V1
    assert descriptor.id == "atlas.auth.fixture"
    assert descriptor.flow_kind is AuthenticationFlowKind.CREDENTIALS
    assert (
        descriptor.presentation.credential_fields[1].kind is CredentialFieldKind.SECRET
    )
    assert descriptor.remote_logout is RemoteLogoutCapability.UNSUPPORTED


def test_descriptor_rejects_flow_incompatible_presentation_and_logout():
    with pytest.raises(ValueError, match="credential fields"):
        AuthenticationProviderDescriptor(
            id="atlas.auth.invalid",
            flow_kind=AuthenticationFlowKind.REDIRECT,
            presentation=_credential_descriptor().presentation,
        )

    with pytest.raises(ValueError, match="remote logout"):
        dataclasses.replace(
            _credential_descriptor(),
            remote_logout=RemoteLogoutCapability.SUPPORTED,
        )


def test_descriptor_rejects_unknown_contract_version():
    with pytest.raises(ValueError, match="unsupported"):
        dataclasses.replace(
            _credential_descriptor(),
            contract_version="atlas.auth.providers.v2",
        )


def test_verified_identity_is_normalized_immutable_and_source_bound():
    attributes = {
        "email": AssuredAttribute(
            "person@example.com", AttributeProvenance.VERIFIED_OWNERSHIP
        )
    }
    identity = VerifiedIdentity(
        provider_id="atlas.auth.fixture",
        source_id="urn:atlas:test-directory",
        subject="person-42",
        profile=ExternalProfile(
            username="person",
            display_name="Test Person",
            email="person@example.com",
        ),
        attributes=attributes,
        groups=ExternalGroupSnapshot.complete(("engineering",)),
    )
    attributes.clear()

    identity.validate_for(
        provider_id="atlas.auth.fixture", source_id="urn:atlas:test-directory"
    )
    assert (
        identity.attributes["email"].provenance
        is AttributeProvenance.VERIFIED_OWNERSHIP
    )
    with pytest.raises(TypeError):
        identity.attributes["other"] = AssuredAttribute(
            "value", AttributeProvenance.SELF_ASSERTED
        )
    with pytest.raises(InvalidAuthenticationResultError, match="provider_id"):
        identity.validate_for(
            provider_id="atlas.auth.other",
            source_id="urn:atlas:test-directory",
        )
    with pytest.raises(InvalidAuthenticationResultError, match="source"):
        identity.validate_for(
            provider_id="atlas.auth.fixture", source_id="urn:atlas:other"
        )


@pytest.mark.parametrize("field_name", ["provider_id", "source_id", "subject"])
def test_verified_identity_rejects_empty_stable_identity_fields(field_name):
    values = {
        "provider_id": "atlas.auth.fixture",
        "source_id": "urn:atlas:test-directory",
        "subject": "subject-1",
    }
    values[field_name] = ""

    with pytest.raises(ValueError, match=field_name.replace("_", " ")):
        VerifiedIdentity(**values)


def test_group_snapshots_distinguish_complete_empty_unavailable_and_unsupported():
    complete_empty = ExternalGroupSnapshot.complete()

    assert complete_empty.status is ExternalGroupSnapshotStatus.COMPLETE
    assert complete_empty.groups == ()
    assert (
        ExternalGroupSnapshot.unavailable().status
        is ExternalGroupSnapshotStatus.UNAVAILABLE
    )
    assert (
        ExternalGroupSnapshot.unsupported().status
        is ExternalGroupSnapshotStatus.UNSUPPORTED
    )
    with pytest.raises(ValueError, match="only a complete"):
        ExternalGroupSnapshot(ExternalGroupSnapshotStatus.UNAVAILABLE, ("engineering",))


def test_credentials_and_callback_parameters_are_immutable_and_redacted():
    credentials = CredentialInput({"username": "person", "password": "secret"})
    callback = RedirectCallbackContext(
        **_flow_kwargs(), callback_parameters={"code": "secret-code"}
    )

    assert "secret" not in repr(credentials)
    assert "secret-code" not in repr(callback)
    with pytest.raises(TypeError):
        credentials.values["password"] = "changed"
    with pytest.raises(ValueError, match="must not be empty"):
        CredentialInput({})


def test_flow_contexts_are_framework_independent_and_require_bounded_deadlines():
    credential_context = CredentialFlowContext(**_flow_kwargs())
    redirect_context = RedirectFlowContext(
        **_flow_kwargs(), callback_url="https://atlas.example/auth/callback"
    )

    assert credential_context.attempt_id == "attempt-1"
    assert redirect_context.callback_url.startswith("https://atlas.example/")
    with pytest.raises(ValueError, match="timezone-aware"):
        CredentialFlowContext(
            **{
                **_flow_kwargs(),
                "deadline": datetime.now(UTC).replace(tzinfo=None),
            }
        )


def test_separate_runtime_protocols_match_only_their_declared_flow() -> None:
    credential = _CredentialProvider()
    redirect = _RedirectProvider()

    assert isinstance(credential, CredentialAuthenticationProvider)
    assert not isinstance(credential, RedirectAuthenticationProvider)
    assert isinstance(redirect, RedirectAuthenticationProvider)
    assert not isinstance(redirect, CredentialAuthenticationProvider)
    assert_type(credential, _CredentialProvider)
    assert_type(redirect, _RedirectProvider)


def test_registry_is_keyed_and_duplicate_diagnostics_name_both_owners():
    registry = AuthenticationProviderRegistry()
    provider = _CredentialProvider()
    registry.register(provider, owner="fixture.one")

    assert registry.get(provider.descriptor.id) is provider
    assert registry.registered_ids() == ("atlas.auth.fixture",)
    with pytest.raises(DuplicateAuthenticationProviderError) as exc_info:
        registry.register(_CredentialProvider(), owner="fixture.two")

    assert exc_info.value.existing_owner == "fixture.one"
    assert exc_info.value.new_owner == "fixture.two"
    assert "fixture.one" in str(exc_info.value)
    assert "fixture.two" in str(exc_info.value)


def test_registry_rejects_runtime_implementation_with_wrong_flow_methods():
    class WrongProvider:
        descriptor = _redirect_descriptor("atlas.auth.wrong")

        def authenticate(self, context, credentials):
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_CREDENTIALS
            )

    with pytest.raises(InvalidAuthenticationProviderError, match="redirect"):
        AuthenticationProviderRegistry().register(WrongProvider())


def test_public_registration_and_lookup_do_not_expose_registry_mutation() -> None:
    registry = authentication_module._authentication_provider_registry
    providers_snapshot = dict(registry._providers)
    owners_snapshot = dict(registry._owners)
    try:
        registry._providers.clear()
        registry._owners.clear()
        provider = _CredentialProvider()

        register_authentication_provider(provider, owner="fixture.plugin")
        lookup = get_authentication_provider_lookup()

        assert_type(lookup, AuthenticationProviderLookup)
        assert lookup.get(provider.descriptor.id) is provider
        assert lookup.all() == (provider,)
        assert not hasattr(lookup, "register")
    finally:
        registry._providers.clear()
        registry._providers.update(providers_snapshot)
        registry._owners.clear()
        registry._owners.update(owners_snapshot)


def test_provider_union_accepts_both_public_protocols() -> None:
    providers: tuple[AuthenticationProvider, ...] = (
        _CredentialProvider(),
        _RedirectProvider(),
    )

    assert len(providers) == 2


def test_authentication_contract_module_is_importable_without_django_setup():
    import atlas_plugin_api.authentication  # noqa: F401
