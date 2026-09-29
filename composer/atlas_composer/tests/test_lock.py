"""Distribution lock file schema tests (`deployment-manifest-and-lock` spec)."""

import pytest
from pydantic import ValidationError

from atlas_composer.lock import (
    Lock,
    LockedBackendArtifact,
    LockedFrontendArtifact,
    LockedPlugin,
    dump_lock,
    load_lock,
)


def _example_lock() -> Lock:
    return Lock(
        distribution="company.atlas@2026.08",
        core="3.2.0",
        plugins={
            "atlas.apis@1.4.2": LockedPlugin(
                backend=LockedBackendArtifact(
                    package="atlas-plugin-apis",
                    version="1.4.2",
                    hash="sha256:example",
                ),
                frontend=LockedFrontendArtifact(
                    package="@atlas/plugin-apis",
                    version="1.4.2",
                    integrity="sha512-example",
                ),
            ),
        },
    )


def test_dump_and_load_round_trip(tmp_path):
    lock_path = tmp_path / "lock.yaml"

    dump_lock(_example_lock(), lock_path)
    reloaded = load_lock(lock_path)

    assert reloaded == _example_lock()


def test_dump_lock_omits_absent_backend_or_frontend(tmp_path):
    lock = Lock(
        distribution="company.atlas@2026.08",
        core="3.2.0",
        plugins={
            "atlas.ingestion@1.0.0": LockedPlugin(
                backend=LockedBackendArtifact(
                    package="atlas-plugin-ingestion",
                    version="1.0.0",
                    hash="sha256:example",
                ),
            ),
        },
    )
    lock_path = tmp_path / "lock.yaml"

    dump_lock(lock, lock_path)

    assert "frontend" not in lock_path.read_text()


def test_locked_plugin_defaults_disabled_to_false():
    locked = LockedPlugin()

    assert locked.disabled is False


def test_dump_lock_omits_disabled_when_false(tmp_path):
    lock = Lock(
        distribution="company.atlas@2026.08",
        core="3.2.0",
        plugins={
            "atlas.ingestion@1.0.0": LockedPlugin(
                backend=LockedBackendArtifact(
                    package="atlas-plugin-ingestion",
                    version="1.0.0",
                    hash="sha256:example",
                ),
            ),
        },
    )
    lock_path = tmp_path / "lock.yaml"

    dump_lock(lock, lock_path)

    assert "\n    disabled:" not in lock_path.read_text()


def test_dump_and_load_round_trips_a_disabled_plugin(tmp_path):
    lock = Lock(
        distribution="company.atlas@2026.08",
        core="3.2.0",
        plugins={
            "atlas.ingestion@1.0.0": LockedPlugin(
                backend=LockedBackendArtifact(
                    package="atlas-plugin-ingestion",
                    version="1.0.0",
                    hash="sha256:example",
                ),
                disabled=True,
            ),
        },
    )
    lock_path = tmp_path / "lock.yaml"

    dump_lock(lock, lock_path)
    reloaded = load_lock(lock_path)

    assert reloaded.plugins["atlas.ingestion@1.0.0"].disabled is True


def test_dump_and_load_preserves_unresolved_plugin_secret_reference(tmp_path):
    lock = _example_lock()
    plugin = lock.plugins["atlas.apis@1.4.2"].model_copy(
        update={
            "config": {
                "fixturePassword": {"fromEnv": "ATLAS_FIXTURE_PASSWORD"},
            },
        }
    )
    lock = lock.model_copy(
        update={
            "plugins": {"atlas.apis@1.4.2": plugin},
        }
    )
    lock_path = tmp_path / "lock.yaml"

    dump_lock(lock, lock_path)
    reloaded = load_lock(lock_path)

    assert reloaded.plugins["atlas.apis@1.4.2"].config == {
        "fixturePassword": {"fromEnv": "ATLAS_FIXTURE_PASSWORD"},
    }
    assert "resolved-password" not in lock_path.read_text()


@pytest.mark.parametrize(
    "secret_field",
    ["clientSecret", "credentials", "accessToken", "refreshToken", "idToken"],
)
def test_lock_schema_rejects_secret_bearing_auth_fields(secret_field):
    provider = {
        "id": "atlas.auth.local",
        "owner": "atlas.catalog",
        "contractVersion": "atlas.auth.providers.v1",
        "flowKind": "credentials",
        "remoteLogout": "unsupported",
        "presentation": {"displayName": "Local"},
        "principalProvisioning": "preprovisioned",
        "actorProvisioning": "manual",
        "profileFields": [],
        "groupSync": {"mode": "none"},
        secret_field: "must-never-be-accepted",
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Lock.model_validate(
            {
                "distribution": "company.atlas@2026.08",
                "core": "3.2.0",
                "plugins": {},
                "auth": {"providers": [provider], "default": "atlas.auth.local"},
            }
        )
