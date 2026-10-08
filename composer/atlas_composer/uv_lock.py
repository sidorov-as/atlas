"""Reads a `uv.lock` file to resolve backend plugin package versions —
the composer's reuse of Python's native lock mechanism (rather than
inventing a third custom lock format), instead of re-resolving packages
independently. Integrity of installed artifacts is left to `uv sync --frozen`,
which verifies the hashes `uv.lock` records.

Replaces `poetry_lock.py` (removed) now that `core/backend` resolves its
dependencies through `uv` instead of Poetry — see the `migrate-backend-to-uv`
change.
"""

from pathlib import Path

import tomllib


def parse_uv_lock(lock_path: Path) -> dict[str, str]:
    """Map each locked package's name to its resolved version."""
    with open(lock_path, "rb") as lock_file:
        data = tomllib.load(lock_file)

    resolved: dict[str, str] = {}
    for package in data.get("package", []):
        source = package.get("source") or {}
        if not (
            source.get("editable") or source.get("directory") or "registry" in source
        ):
            # `virtual` (the workspace root itself) or a source this
            # composer doesn't resolve yet (e.g. `git`) — skip.
            continue
        resolved[package["name"]] = package["version"]
    return resolved
