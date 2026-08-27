from datetime import UTC, datetime, timedelta

from atlas_auth_contract_fixture import (
    PROVIDER_ID,
    SOURCE_ID,
    FixtureCredentialProvider,
)
from atlas_plugin_api import (
    CredentialFlowContext,
    CredentialInput,
    CredentialProviderContractHooks,
    run_credential_provider_contract,
)


def test_fixture_provider_obeys_the_published_contract():
    stored_rows = []
    core_state = {"session": None, "permissions": ()}
    hooks = CredentialProviderContractHooks(
        provider_factory=FixtureCredentialProvider,
        context_factory=lambda: CredentialFlowContext(
            provider_id=PROVIDER_ID,
            source_id=SOURCE_ID,
            attempt_id="attempt-1",
            correlation_id="correlation-1",
            deadline=datetime.now(UTC) + timedelta(seconds=30),
        ),
        valid_credentials_factory=lambda: CredentialInput(
            {"username": "person", "password": "fixture"}
        ),
        invalid_credentials_factory=lambda: CredentialInput(
            {"username": "person", "password": "wrong"}
        ),
        unavailable_credentials_factory=lambda: CredentialInput(
            {"username": "unavailable", "password": "fixture"}
        ),
        state_probe=lambda: dict(core_state),
        persistence_probe=lambda: tuple(stored_rows),
    )

    run_credential_provider_contract(hooks)
