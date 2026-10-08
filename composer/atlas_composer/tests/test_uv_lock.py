"""`uv.lock` reader tests, exercised against this monorepo's own
`core/backend/uv.lock` (`deployment-manifest-and-lock` spec: reuse
Python's native lock mechanism; integrity stays with `uv sync --frozen`)."""

from pathlib import Path

from atlas_composer.uv_lock import parse_uv_lock

REPO_ROOT = Path(__file__).resolve().parents[3]
UV_LOCK = REPO_ROOT / "core" / "backend" / "uv.lock"


def test_resolves_a_registry_package_version():
    assert parse_uv_lock(UV_LOCK)["pydantic"] == "2.13.5"


def test_resolves_a_workspace_package_version():
    assert parse_uv_lock(UV_LOCK)["atlas-plugin-standard-catalog"] == "0.1.0"


def test_resolving_is_deterministic():
    assert parse_uv_lock(UV_LOCK) == parse_uv_lock(UV_LOCK)
