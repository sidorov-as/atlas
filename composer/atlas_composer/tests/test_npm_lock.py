"""`package-lock.json` reader tests, exercised against this monorepo's own
root `package-lock.json` (`deployment-manifest-and-lock` spec: reuse npm's
native lock mechanism; integrity stays with `npm ci`)."""

from pathlib import Path

from atlas_composer.npm_lock import parse_npm_lock

REPO_ROOT = Path(__file__).resolve().parents[3]
NPM_LOCK = REPO_ROOT / "package-lock.json"


def test_resolves_a_workspace_package_version():
    assert parse_npm_lock(NPM_LOCK)["@atlas/plugin-standard-catalog"] == "0.1.0"


def test_resolving_is_deterministic():
    assert parse_npm_lock(NPM_LOCK) == parse_npm_lock(NPM_LOCK)
