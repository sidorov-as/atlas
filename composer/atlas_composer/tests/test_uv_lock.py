"""`uv.lock` reader tests, exercised against this monorepo's own
`core/backend/uv.lock` (`deployment-manifest-and-lock` spec: reuse
Python's native lock mechanism rather than re-deriving hashes)."""

from pathlib import Path

from atlas_composer.uv_lock import parse_uv_lock

REPO_ROOT = Path(__file__).resolve().parents[3]
UV_LOCK = REPO_ROOT / "core" / "backend" / "uv.lock"


def test_resolves_a_registry_package_hash_verbatim():
    resolved = parse_uv_lock(UV_LOCK)

    pydantic = resolved["pydantic"]

    assert pydantic.version == "2.13.5"
    assert pydantic.hash.startswith("sha256:")


def test_resolves_a_workspace_package_via_directory_hash():
    resolved = parse_uv_lock(UV_LOCK)

    standard_catalog = resolved["atlas-plugin-standard-catalog"]

    assert standard_catalog.version == "0.1.0"
    assert standard_catalog.hash.startswith("sha256:")


def test_resolving_a_workspace_package_is_deterministic():
    first = parse_uv_lock(UV_LOCK)["atlas-plugin-standard-catalog"]
    second = parse_uv_lock(UV_LOCK)["atlas-plugin-standard-catalog"]

    assert first.hash == second.hash
