"""Reads a `package-lock.json` file to resolve frontend plugin package
metadata — the composer's reuse of npm's native lock mechanism, instead of re-resolving or re-hashing packages independently.
"""

import base64
import json
from dataclasses import dataclass
from pathlib import Path

from ._hashing import hash_directory


@dataclass(frozen=True, slots=True)
class ResolvedFrontendPackage:
    version: str
    integrity: str
    """`sha512-<base64>`. Reused verbatim from `package-lock.json`'s own
    recorded integrity when the package was resolved from a real registry;
    computed from the package's source directory when the lock records it
    as a local workspace link (a `workspace`-sourced plugin in this
    monorepo, which carries no registry integrity value of its own)."""


def parse_npm_lock(lock_path: Path) -> dict[str, ResolvedFrontendPackage]:
    """Map each locked package's name to its resolved version and integrity."""
    with open(lock_path) as lock_file:
        data = json.load(lock_file)

    resolved: dict[str, ResolvedFrontendPackage] = {}
    for key, entry in data.get("packages", {}).items():
        name = entry.get("name")
        version = entry.get("version")
        if not key or not name or not version:
            # `""` is the root project entry; a `node_modules/` alias entry
            # for a workspace link carries neither `name` nor `version` —
            # the workspace member's own entry (keyed by its directory) does.
            continue
        integrity = entry.get("integrity")
        if not integrity:
            # A local workspace member: its `packages` key IS its directory,
            # relative to the lockfile — no registry integrity to reuse, so
            # hash the directory ourselves.
            package_dir = (lock_path.parent / key).resolve()
            integrity = (
                "sha512-"
                + base64.b64encode(
                    hash_directory(package_dir, algorithm="sha512"),
                ).decode()
            )
        resolved[name] = ResolvedFrontendPackage(
            version=version,
            integrity=integrity,
        )
    return resolved
