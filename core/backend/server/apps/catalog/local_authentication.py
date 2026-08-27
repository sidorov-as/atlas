"""Core-owned local credential provider using the public provider contract."""

from collections.abc import Callable
from typing import Any

from atlas_plugin_api import (
    AuthenticationFailure,
    AuthenticationFailureCategory,
    CredentialFlowContext,
    CredentialInput,
    ExternalGroupSnapshot,
    ExternalProfile,
    VerifiedIdentity,
)
from django.contrib.auth.backends import ModelBackend

from .auth_descriptors import LOCAL_PROVIDER_DESCRIPTOR


def _verify_local_user(_request: object, *, username: str, password: str):
    return ModelBackend().authenticate(
        None, username=username, password=password
    )


class LocalCredentialProvider:
    """Verify a pre-existing Django Principal without creating a session."""

    descriptor = LOCAL_PROVIDER_DESCRIPTOR

    def __init__(
        self, authenticate_user: Callable[..., Any] = _verify_local_user
    ) -> None:
        self._authenticate_user = authenticate_user

    def authenticate(
        self,
        context: CredentialFlowContext,
        credentials: CredentialInput,
    ) -> VerifiedIdentity | AuthenticationFailure:
        username = credentials.values.get("username")
        password = credentials.values.get("password")
        if not username or not password:
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_CREDENTIALS
            )
        try:
            user = self._authenticate_user(
                None, username=username, password=password
            )
        except Exception:
            return AuthenticationFailure(
                AuthenticationFailureCategory.UNAVAILABLE, retryable=True
            )
        if user is None or not user.is_active:
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_CREDENTIALS
            )
        return VerifiedIdentity(
            provider_id=self.descriptor.id,
            source_id=context.source_id,
            subject=str(user.pk),
            profile=ExternalProfile(
                username=user.get_username(),
                display_name=user.get_full_name() or None,
                email=user.email or None,
            ),
            groups=ExternalGroupSnapshot.unsupported(),
        )
