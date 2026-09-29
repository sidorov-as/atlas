from __future__ import annotations

from pathlib import Path

from atlas_composer.lock import load_lock
from atlas_composer.manifest import load_manifest

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DISTRIBUTION = REPO_ROOT / "distributions" / "default"


def test_official_distribution_keeps_explicit_conservative_local_auth() -> None:
    manifest = load_manifest(DEFAULT_DISTRIBUTION / "manifest.yaml")
    lock = load_lock(DEFAULT_DISTRIBUTION / "lock.yaml")

    assert [provider.id for provider in manifest.auth.providers] == ["atlas.auth.local"]
    provider = manifest.auth.providers[0]
    assert manifest.auth.default == "atlas.auth.local"
    assert provider.signup == "disabled"
    assert provider.principal_provisioning == "preprovisioned"
    assert provider.actor_provisioning == "manual"
    assert [provider.id for provider in lock.auth.providers] == ["atlas.auth.local"]
    assert lock.auth.default == "atlas.auth.local"
