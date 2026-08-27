"""Shared repository-relative path validation.

Two entry points share the same syntactic rejection rules (empty, absolute,
`..`-containing, or NUL/control-character entries):

- `resolve_repository_relative_entry` is the pre-check `pipeline.py`'s
  `Include.spec.paths` resolution and `database_schema.py`'s `sourceSqlPath`
  resolution can run *before* a real checkout exists — both work purely on
  repository-relative path strings at that point (`SourceConnector` exposes
  no filesystem path), so this cannot itself detect a symlink that stays
  syntactically in-bounds but escapes on disk.
- `resolve_repository_relative` is the full check, run once a real checkout
  directory exists (`connectors/git.py`'s `_Checkout.read`): it re-verifies
  the same syntactic rules independently of whichever caller resolved the
  path (so a future caller of `fetch_file` that forgets to pre-validate
  still can't escape the checkout), and additionally resolves the candidate
  against `checkout_root` and confirms containment, which also catches a
  symlink that stays in-bounds syntactically but points outside the checkout
  on disk).

Mirrors `models.py`'s existing `validate_repository_path` discipline for
`RegisteredRepository.path` (reject empty, absolute, `..`-containing, or
control-character paths) but is reject-not-raise (returns `None` rather than
raising `ValidationError`), since callers here treat a bad path as a failed
resolution to record as an `IngestionIssue`, not a hard error.
"""

import re
from pathlib import Path, PurePosixPath

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")


def _is_syntactically_valid_entry(entry: str) -> bool:
    if not entry or _CONTROL_CHAR_RE.search(entry):
        return False
    return not PurePosixPath(entry).is_absolute()


def resolve_repository_relative_entry(
    base_dir: PurePosixPath,
    entry: str,
) -> str | None:
    """`entry` resolved relative to `base_dir`, as a repository-relative path
    string — or `None` if `entry` is empty, absolute, contains a `..`
    segment, or a NUL/control character. No real checkout is required (or
    consulted), so this cannot detect a symlink escape — see module
    docstring."""
    if not _is_syntactically_valid_entry(entry):
        return None

    candidate = PurePosixPath(base_dir, entry)
    if ".." in candidate.parts:
        return None

    return str(candidate)


def resolve_repository_relative(
    base_dir: PurePosixPath,
    entry: str,
    checkout_root: Path,
) -> Path | None:
    """`entry` resolved relative to `base_dir`, as an absolute path under
    `checkout_root` — or `None` if `entry` is empty, absolute, contains a
    `..` segment or a NUL/control character, or resolves (following any
    symlinks) outside `checkout_root`.

    Symlink escapes are caught because `Path.resolve()` follows symlinks to
    their real target before the `is_relative_to` containment check runs.
    """
    if not _is_syntactically_valid_entry(entry):
        return None

    candidate = PurePosixPath(base_dir, entry)
    if ".." in candidate.parts:
        return None

    resolved_root = checkout_root.resolve()
    resolved_candidate = (checkout_root / candidate).resolve()
    if not resolved_candidate.is_relative_to(resolved_root):
        return None

    return resolved_candidate
