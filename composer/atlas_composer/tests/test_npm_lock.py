"""`package-lock.json` reader tests, exercised against this monorepo's own
root `package-lock.json` (`deployment-manifest-and-lock` spec: reuse npm's
native lock mechanism rather than re-deriving integrity independently)."""

from pathlib import Path

from atlas_composer.npm_lock import parse_npm_lock

REPO_ROOT = Path(__file__).resolve().parents[3]
NPM_LOCK = REPO_ROOT / "package-lock.json"


def test_resolves_a_workspace_package_via_directory_hash():
    resolved = parse_npm_lock(NPM_LOCK)

    standard_catalog = resolved["@atlas/plugin-standard-catalog"]

    assert standard_catalog.version == "0.1.0"
    assert standard_catalog.integrity.startswith("sha512-")


def test_resolving_a_workspace_package_is_deterministic():
    first = parse_npm_lock(NPM_LOCK)["@atlas/plugin-standard-catalog"]
    second = parse_npm_lock(NPM_LOCK)["@atlas/plugin-standard-catalog"]

    assert first.integrity == second.integrity
