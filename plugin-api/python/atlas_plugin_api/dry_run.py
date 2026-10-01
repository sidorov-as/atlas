"""Dry-run support for authoring writes (`mcp-write-preview` spec).

`dry_run()` runs the caller's real service call inside a savepoint that is
always rolled back, so authorization, validation, reference resolution, and
constraint checks are the real ones while nothing — rows, audit records,
`on_commit` hooks — survives. Effects outside the database transaction must
check `is_dry_run()` and skip themselves, reporting what they skipped with
`add_dry_run_warning()` (for example the API spec URL fetch).

Lives here, not in `atlas.mcp`, so a plugin that owns an outbound side effect
can honor a dry-run without importing the MCP plugin.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from django.db import transaction


@dataclass
class DryRunContext:
    warnings: list[str] = field(default_factory=list)


_current: ContextVar[DryRunContext | None] = ContextVar("atlas_dry_run", default=None)


def is_dry_run() -> bool:
    return _current.get() is not None


def add_dry_run_warning(message: str) -> None:
    """Record a warning on the active dry-run; a no-op outside one."""
    context = _current.get()
    if context is not None and message not in context.warnings:
        context.warnings.append(message)


@contextmanager
def dry_run() -> Iterator[DryRunContext]:
    """Open a dry-run: everything written inside is rolled back on exit,
    whether the block returns or raises."""
    context = DryRunContext()
    token = _current.set(context)
    try:
        with transaction.atomic():
            yield context
            transaction.set_rollback(True)
    finally:
        _current.reset(token)
