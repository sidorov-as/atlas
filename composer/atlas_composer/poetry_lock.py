"""Reads a `poetry.lock` file to resolve backend plugin package metadata —
the composer's reuse of Python's native lock mechanism (rather than
inventing a third custom lock format), instead of
re-resolving or re-hashing packages independently.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from ._hashing import hash_directory


@dataclass(frozen=True, slots=True)
class ResolvedPythonPackage:
    version: str
    hash: str
    """`sha256:<hex>`. Reused verbatim from `poetry.lock`'s own recorded
    hash when the package was resolved from a real index; computed from the
    package's source directory when `poetry.lock` records it as a local
    `directory` source (a `workspace` path dependency, which carries no
    registry hash of its own)."""


def parse_poetry_lock(lock_path: Path) -> dict[str, ResolvedPythonPackage]:
    """Map each locked package's name to its resolved version and hash."""
    with open(lock_path, 'rb') as lock_file:
        data = tomllib.load(lock_file)

    resolved: dict[str, ResolvedPythonPackage] = {}
    for package in data.get('package', []):
        files = package.get('files') or []
        if files:
            package_hash = files[0]['hash']
        else:
            source = package.get('source') or {}
            if source.get('type') != 'directory':
                # No registry hash, and not a local directory we can hash
                # ourselves (e.g. a git source) — nothing this composer can
                # resolve for it yet.
                continue
            package_dir = (lock_path.parent / source['url']).resolve()
            package_hash = 'sha256:' + hash_directory(
                package_dir, algorithm='sha256',
            ).hex()
        resolved[package['name']] = ResolvedPythonPackage(
            version=package['version'], hash=package_hash,
        )
    return resolved
