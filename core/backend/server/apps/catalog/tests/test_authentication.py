"""First-party local provider conformance and session regressions."""

from datetime import timedelta

import pytest
from atlas_plugin_api import (
    AuthenticationFailure,
    AuthenticationFailureCategory,
    CredentialFlowContext,
    CredentialInput,
    CredentialProviderContractHooks,
    get_authentication_provider_lookup,
    run_credential_provider_contract,
)
from django.utils import timezone

from server.apps.catalog.auth_descriptors import (
    LOCAL_PROVIDER_ID,
    LOCAL_SOURCE_ID,
)
from server.apps.catalog.local_authentication import LocalCredentialProvider

pytestmark = pytest.mark.django_db


def _context() -> CredentialFlowContext:
    return CredentialFlowContext(
        provider_id=LOCAL_PROVIDER_ID,
        source_id=LOCAL_SOURCE_ID,
        attempt_id="local-contract-attempt",
        correlation_id="local-contract-correlation",
        deadline=timezone.now() + timedelta(minutes=1),
    )


def test_local_runtime_is_registered_through_public_lookup():
    provider = get_authentication_provider_lookup().get(LOCAL_PROVIDER_ID)

    assert isinstance(provider, LocalCredentialProvider)
    assert provider.descriptor.id == LOCAL_PROVIDER_ID


def test_local_provider_returns_safe_failure_for_empty_or_invalid_credentials():
    provider = LocalCredentialProvider(lambda *args, **kwargs: None)

    invalid = provider.authenticate(
        _context(), CredentialInput({"username": "person", "password": "bad"})
    )

    assert invalid == AuthenticationFailure(
        AuthenticationFailureCategory.INVALID_CREDENTIALS
    )


def test_local_provider_sanitizes_backend_failure():
    def unavailable(*args, **kwargs):
        raise RuntimeError("database details that must not escape")

    result = LocalCredentialProvider(unavailable).authenticate(
        _context(),
        CredentialInput({"username": "person", "password": "secret-value"}),
    )

    assert result == AuthenticationFailure(
        AuthenticationFailureCategory.UNAVAILABLE, retryable=True
    )
    assert "secret-value" not in repr(result)


def test_local_provider_passes_public_credential_contract(owner_account):
    owner_account.set_password("correct horse battery staple")
    owner_account.save(update_fields=("password",))

    def verify(_request, *, username, password):
        if username == "provider-down":
            raise RuntimeError("backend unavailable")
        if username == owner_account.username and owner_account.check_password(
            password
        ):
            return owner_account
        return None

    run_credential_provider_contract(
        CredentialProviderContractHooks(
            provider_factory=lambda: LocalCredentialProvider(verify),
            context_factory=_context,
            valid_credentials_factory=lambda: CredentialInput(
                {
                    "username": owner_account.username,
                    "password": "correct horse battery staple",
                }
            ),
            invalid_credentials_factory=lambda: CredentialInput(
                {"username": owner_account.username, "password": "incorrect"}
            ),
            unavailable_credentials_factory=lambda: CredentialInput(
                {"username": "provider-down", "password": "not-persisted"}
            ),
        )
    )
