"""Deterministic disposable identities using only public SDK types."""

from __future__ import annotations

import hmac
from dataclasses import dataclass

from atlas_plugin_api import (
    AssuredAttribute,
    AttributeProvenance,
    AuthenticationFailure,
    AuthenticationFailureCategory,
    CredentialFlowContext,
    CredentialInput,
    ExternalGroupSnapshot,
    ExternalProfile,
    VerifiedIdentity,
)

from .config import FixtureCredentialConfig
from .plugin import PROVIDER_DESCRIPTOR, PROVIDER_ID


@dataclass(frozen=True, slots=True)
class _FixtureIdentity:
    subject: str
    username: str
    display_name: str
    email: str
    groups: ExternalGroupSnapshot


_FIXTURES = {
    "fixture-alice": _FixtureIdentity(
        subject="fixture-user-alice-v1",
        username="fixture-alice",
        display_name="Fixture Alice",
        email="fixture-alice@example.invalid",
        groups=ExternalGroupSnapshot.complete(("fixture-platform",)),
    ),
    "fixture-empty": _FixtureIdentity(
        subject="fixture-user-empty-v1",
        username="fixture-empty",
        display_name="Fixture Empty Groups",
        email="fixture-empty@example.invalid",
        groups=ExternalGroupSnapshot.complete(),
    ),
    "fixture-groups-unavailable": _FixtureIdentity(
        subject="fixture-user-unavailable-groups-v1",
        username="fixture-groups-unavailable",
        display_name="Fixture Unavailable Groups",
        email="fixture-groups-unavailable@example.invalid",
        groups=ExternalGroupSnapshot.unavailable(),
    ),
}


def configured_fixture() -> FixtureCredentialConfig:
    from atlas_plugin_api import get_plugin_config

    config = get_plugin_config(PROVIDER_ID, FixtureCredentialConfig)
    if config.has_unresolved_secrets():
        raise RuntimeError(
            "fixture provider has no resolved typed configuration"
        )
    return config


class FixtureCredentialProvider:
    descriptor = PROVIDER_DESCRIPTOR

    def __init__(self, config: FixtureCredentialConfig) -> None:
        if not config.development_enabled:
            raise ValueError("fixture provider is disabled outside development")
        if not isinstance(config.fixture_password, str):
            raise TypeError("fixture password must be resolved before runtime")
        self._source_id = config.source_id
        self._password = config.fixture_password

    def authenticate(
        self,
        context: CredentialFlowContext,
        credentials: CredentialInput,
    ) -> VerifiedIdentity | AuthenticationFailure:
        if (
            context.provider_id != PROVIDER_ID
            or context.source_id != self._source_id
        ):
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_RESULT
            )

        username = credentials.values.get("username", "")
        password = credentials.values.get("password", "")
        if username == "fixture-provider-outage":
            return AuthenticationFailure(
                AuthenticationFailureCategory.UNAVAILABLE,
                retryable=True,
            )

        identity = _FIXTURES.get(username)
        password_matches = hmac.compare_digest(password, self._password)
        if identity is None or not password or not password_matches:
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_CREDENTIALS
            )

        return VerifiedIdentity(
            provider_id=PROVIDER_ID,
            source_id=self._source_id,
            subject=identity.subject,
            profile=ExternalProfile(
                username=identity.username,
                display_name=identity.display_name,
                email=identity.email,
            ),
            attributes={
                "email": AssuredAttribute(
                    identity.email,
                    AttributeProvenance.VERIFIED_OWNERSHIP,
                ),
                "displayName": AssuredAttribute(
                    identity.display_name,
                    AttributeProvenance.AUTHORITY_MANAGED,
                ),
            },
            groups=identity.groups,
        )
