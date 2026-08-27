from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest
from atlas_plugin_api import (
    AuthenticationFailure,
    AuthenticationFailureCategory,
    CredentialFlowContext,
    CredentialInput,
    CredentialProviderContractHooks,
    ExternalGroupSnapshotStatus,
    SecretRef,
    VerifiedIdentity,
    run_credential_provider_contract,
)
from pydantic import ValidationError

from atlas_example_auth_fixture.config import FixtureCredentialConfig
from atlas_example_auth_fixture.plugin import PLUGIN, PROVIDER_ID
from atlas_example_auth_fixture.provider import FixtureCredentialProvider

SOURCE_ID = "urn:atlas:directory:fixture-custom-credentials-example"
PASSWORD = "fixture-only-9Cedar-Sky-4"


def _config(**overrides) -> FixtureCredentialConfig:
    values = {
        "developmentEnabled": True,
        "sourceId": SOURCE_ID,
        "fixturePassword": PASSWORD,
    }
    values.update(overrides)
    return FixtureCredentialConfig.model_validate(values)


def _context() -> CredentialFlowContext:
    return CredentialFlowContext(
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        attempt_id="fixture-attempt",
        correlation_id="fixture-correlation",
        deadline=datetime.now(UTC) + timedelta(seconds=30),
    )


def test_static_descriptor_is_importable_without_django_setup() -> None:
    environment = dict(os.environ)
    environment.pop("DJANGO_SETTINGS_MODULE", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from atlas_example_auth_fixture.plugin import PLUGIN; "
            "print(PLUGIN.id)",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == PROVIDER_ID


def test_config_requires_development_gate_and_secret_reference() -> None:
    with pytest.raises(ValidationError, match="developmentEnabled"):
        _config(developmentEnabled=False)

    config = _config(fixturePassword={"fromEnv": "ATLAS_FIXTURE_PASSWORD"})
    assert isinstance(config.fixture_password, SecretRef)
    assert config.has_unresolved_secrets()


def test_deterministic_profiles_assurance_and_group_states() -> None:
    provider = FixtureCredentialProvider(_config())

    alice = provider.authenticate(
        _context(),
        CredentialInput({"username": "fixture-alice", "password": PASSWORD}),
    )
    empty = provider.authenticate(
        _context(),
        CredentialInput({"username": "fixture-empty", "password": PASSWORD}),
    )
    unavailable = provider.authenticate(
        _context(),
        CredentialInput(
            {
                "username": "fixture-groups-unavailable",
                "password": PASSWORD,
            }
        ),
    )

    assert isinstance(alice, VerifiedIdentity)
    assert alice.subject == "fixture-user-alice-v1"
    assert alice.attributes["email"].provenance.value == "verified_ownership"
    assert alice.groups.groups == ("fixture-platform",)
    assert isinstance(empty, VerifiedIdentity)
    assert empty.groups.status is ExternalGroupSnapshotStatus.COMPLETE
    assert empty.groups.groups == ()
    assert isinstance(unavailable, VerifiedIdentity)
    assert unavailable.groups.status is ExternalGroupSnapshotStatus.UNAVAILABLE


@pytest.mark.parametrize("username", ["missing-user", "fixture-alice"])
def test_invalid_credentials_hide_account_existence(username) -> None:
    result = FixtureCredentialProvider(_config()).authenticate(
        _context(), CredentialInput({"username": username, "password": "wrong"})
    )

    assert result == AuthenticationFailure(
        AuthenticationFailureCategory.INVALID_CREDENTIALS
    )


def test_simulated_provider_outage_is_safe_and_retryable() -> None:
    result = FixtureCredentialProvider(_config()).authenticate(
        _context(),
        CredentialInput(
            {"username": "fixture-provider-outage", "password": PASSWORD}
        ),
    )

    assert result == AuthenticationFailure(
        AuthenticationFailureCategory.UNAVAILABLE,
        retryable=True,
    )
    assert PASSWORD not in repr(result)


def test_fixture_provider_passes_public_credential_contract() -> None:
    persistence = []
    core_state = {"session": None, "permissions": ()}
    hooks = CredentialProviderContractHooks(
        provider_factory=lambda: FixtureCredentialProvider(_config()),
        context_factory=_context,
        valid_credentials_factory=lambda: CredentialInput(
            {"username": "fixture-alice", "password": PASSWORD}
        ),
        invalid_credentials_factory=lambda: CredentialInput(
            {"username": "fixture-alice", "password": "wrong-password"}
        ),
        unavailable_credentials_factory=lambda: CredentialInput(
            {"username": "fixture-provider-outage", "password": PASSWORD}
        ),
        state_probe=lambda: dict(core_state),
        persistence_probe=lambda: tuple(persistence),
    )

    run_credential_provider_contract(hooks)


def test_descriptor_uses_only_exact_group_sync() -> None:
    contribution = PLUGIN.authentication_providers[0]
    assert contribution.descriptor.id == PROVIDER_ID
    assert contribution.config_schema is FixtureCredentialConfig
    assert contribution.source_id_config_field == "source_id"
    assert contribution.supported_group_sync_modes == ("exact",)
