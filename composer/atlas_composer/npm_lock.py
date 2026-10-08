"""Reads a `package-lock.json` file to resolve frontend plugin package
versions — the composer's reuse of npm's native lock mechanism, instead of
re-resolving packages independently. Integrity of installed artifacts is left
to `npm ci`, which verifies the values `package-lock.json` records.
"""

import json
from pathlib import Path


def parse_npm_lock(lock_path: Path) -> dict[str, str]:
    """Map each locked package's name to its resolved version."""
    with open(lock_path) as lock_file:
        data = json.load(lock_file)

    resolved: dict[str, str] = {}
    for key, entry in data.get("packages", {}).items():
        name = entry.get("name")
        version = entry.get("version")
        if not key or not name or not version:
            # `""` is the root project entry; a `node_modules/` alias entry
            # for a workspace link carries neither `name` nor `version` —
            # the workspace member's own entry (keyed by its directory) does.
            continue
        resolved[name] = version
    return resolved
