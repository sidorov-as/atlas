"""Deterministic content hash for a local workspace package directory.

Used by `uv_lock.py` and `npm_lock.py` when a native lock records a
package as a local path/link source (a `workspace`-sourced plugin in this
monorepo) with no registry-issued hash to reuse.
"""

import hashlib
import subprocess
from collections.abc import Iterator
from pathlib import Path

_EXCLUDED_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".venv",
        "node_modules",
        "dist",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)


def hash_directory(directory: Path, *, algorithm: str) -> bytes:
    """Hash every source file's relative path and bytes, sorted by path so
    the result doesn't depend on filesystem iteration order."""
    digest = hashlib.new(algorithm)
    for path in _tracked_files(directory):
        digest.update(str(path.relative_to(directory)).encode())
        digest.update(path.read_bytes())

    return digest.digest()


def _tracked_files(directory: Path) -> Iterator[Path]:
    """Files under `directory` that belong to the package's source.

    Inside a git checkout that is what git considers part of the tree —
    tracked files plus new ones not yet added, minus anything ignored — so a
    developer's local scratch files can't make the hash differ from CI's.
    Outside git (e.g. a build context without `.git`) it falls back to every
    file on disk."""
    paths = _git_listed_files(directory)
    if paths is None:
        paths = (path for path in directory.rglob("*") if path.is_file())

    return iter(
        sorted(
            path
            for path in paths
            if _EXCLUDED_DIR_NAMES.isdisjoint(path.relative_to(directory).parts)
        )
    )


def _git_listed_files(directory: Path) -> list[Path] | None:
    try:
        completed = subprocess.run(
            [
                "git",
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
                "--",
                ".",
            ],
            cwd=directory,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    names = completed.stdout.decode().split("\0")
    # `--cached` still lists files deleted from disk but not yet staged.
    return [path for name in names if name and (path := directory / name).is_file()]
