"""`poetry.lock` reader tests, exercised against this monorepo's own
`core/backend/poetry.lock` (`deployment-manifest-and-lock` spec: reuse
Python's native lock mechanism rather than re-deriving hashes)."""

from pathlib import Path

from atlas_composer.poetry_lock import parse_poetry_lock

REPO_ROOT = Path(__file__).resolve().parents[3]
POETRY_LOCK = REPO_ROOT / 'core' / 'backend' / 'poetry.lock'


def test_resolves_a_registry_package_hash_verbatim():
    resolved = parse_poetry_lock(POETRY_LOCK)

    pydantic = resolved['pydantic']

    assert pydantic.version == '2.13.4'
    assert pydantic.hash.startswith('sha256:')


def test_resolves_a_workspace_package_via_directory_hash():
    resolved = parse_poetry_lock(POETRY_LOCK)

    standard_catalog = resolved['atlas-plugin-standard-catalog']

    assert standard_catalog.version == '0.1.0'
    assert standard_catalog.hash.startswith('sha256:')


def test_resolving_a_workspace_package_is_deterministic():
    first = parse_poetry_lock(POETRY_LOCK)['atlas-plugin-standard-catalog']
    second = parse_poetry_lock(POETRY_LOCK)['atlas-plugin-standard-catalog']

    assert first.hash == second.hash
