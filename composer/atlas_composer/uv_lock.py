"""Reads a `uv.lock` file to resolve backend plugin package metadata —
the composer's reuse of Python's native lock mechanism (rather than
inventing a third custom lock format), instead of
re-resolving or re-hashing packages independently.

Replaces `poetry_lock.py` (removed) now that `core/backend` resolves its
dependencies through `uv` instead of Poetry — see the `migrate-backend-to-uv`
change.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from ._hashing import hash_directory


@dataclass(frozen=True, slots=True)
class ResolvedPythonPackage:
    version: str
    hash: str
    """`sha256:<hex>`. Reused verbatim from `uv.lock`'s own recorded wheel
    (or, absent a wheel, sdist) hash when the package was resolved from a
    real index; computed from the package's source directory when
    `uv.lock` records it as a local `editable`/`directory` source (a
    `workspace` path dependency, which carries no registry hash of its
    own)."""


def parse_uv_lock(lock_path: Path) -> dict[str, ResolvedPythonPackage]:
    """Map each locked package's name to its resolved version and hash."""
    with open(lock_path, "rb") as lock_file:
        data = tomllib.load(lock_file)

    resolved: dict[str, ResolvedPythonPackage] = {}
    for package in data.get("package", []):
        source = package.get("source") or {}
        local_path = source.get("editable") or source.get("directory")
        if local_path is not None:
            package_dir = (lock_path.parent / local_path).resolve()
            package_hash = (
                "sha256:"
                + hash_directory(
                    package_dir,
                    algorithm="sha256",
                ).hex()
            )
        elif "registry" in source:
            wheels = package.get("wheels") or []
            sdist = package.get("sdist") or {}
            if wheels:
                package_hash = wheels[0]["hash"]
            elif sdist.get("hash"):
                package_hash = sdist["hash"]
            else:
                # No hash recorded for this registry entry — nothing this
                # composer can resolve for it yet.
                continue
        else:
            # `virtual` (the workspace root itself) or a source this
            # composer doesn't resolve yet (e.g. `git`) — skip.
            continue
        resolved[package["name"]] = ResolvedPythonPackage(
            version=package["version"],
            hash=package_hash,
        )
    return resolved
