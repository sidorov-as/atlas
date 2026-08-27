"""Purge reference-scan extension point (`entity-removal-lifecycle` spec:
"Purge validation scans both FK-backed and ref-string-backed references").

D8's mitigation for the ref-string blind-spot risk calls for implementing
Purge's reference scan "as a registered/extensible check (not hardcoded to
Flow) so future non-FK reference mechanisms can register their own scan" —
same keyed-registry shape as `atlas_plugin_apis.extension_points`'s
`delete_guards`, but generalized: Purge applies across every purgeable kind
(System/Component/Resource/API), not one plugin's own kind, so the registry
lives here rather than inside any single plugin, and Core's
`EntityService.purge()` runs every registered scanner without importing any
plugin's models directly.

A plugin holding a reference to another kind's entity (`atlas_plugin_
standard_catalog`'s `ComponentDetails.depends_on`/`provides_apis`/
`consumes_apis`, `atlas_plugin_flows`'s Flow step `entity_ref`) registers one
scanner per plugin during its `register_runtime()`, self-filtering by
`entity.kind` since it's called for every purge regardless of kind.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .catalog import CatalogEntity

__all__ = [
    "DuplicatePurgeScannerError",
    "PurgeReference",
    "PurgeScanner",
    "PurgeScannerRegistry",
    "purge_scanners",
    "register_purge_scanner",
    "run_purge_scan",
]


@dataclass(frozen=True)
class PurgeReference:
    """One reference to the entity being purged, discovered by a scanner.

    `label` names the referencing thing, for the blocked-purge error's named
    list. `active` distinguishes a still-live reference (blocks the purge)
    from one whose own referencing entity is itself already removed/inactive
    (the purge proceeds and, if `cascade` is given, calls it to clean up
    that reference row as part of the same operation) — the spec's "cascades
    cleanup of purely-removed-status references" behavior.
    """

    label: str
    active: bool
    cascade: Callable[[], None] | None = None


PurgeScanner = Callable[[CatalogEntity], "Iterable[PurgeReference]"]


class DuplicatePurgeScannerError(ValueError):
    """Raised when a second registration tries to claim an already-registered owner id."""

    def __init__(self, owner: str) -> None:
        super().__init__(f"A purge scanner is already registered by owner={owner!r}")
        self.owner = owner


class PurgeScannerRegistry:
    """Maps a registering plugin id to its purge reference scanner — same shape as
    `atlas_plugin_apis.extension_points.DeleteGuardRegistry`, so tests that run real
    runtime hooks repeatedly can swap in a fresh instance the same way."""

    def __init__(self) -> None:
        self._scanners: dict[str, PurgeScanner] = {}

    def register(self, owner: str, scanner: PurgeScanner) -> None:
        if owner in self._scanners:
            raise DuplicatePurgeScannerError(owner)
        self._scanners[owner] = scanner

    def run(self, entity: CatalogEntity) -> list[PurgeReference]:
        """Run every registered scanner against `entity`, in registration order,
        collecting every reference each one reports."""
        references: list[PurgeReference] = []
        for scanner in self._scanners.values():
            references.extend(scanner(entity))
        return references


# Process-wide registry populated by the runtime entry-point-loading phase —
# one registry for the whole process, matching `atlas_plugin_api.kinds.registry`.
purge_scanners = PurgeScannerRegistry()


def register_purge_scanner(owner: str, scanner: PurgeScanner) -> None:
    """Register `scanner`, called with the entity being purged (any kind) —
    it self-filters by `entity.kind` and returns the references it found
    (possibly empty). `owner` identifies the registering plugin; each plugin
    registers at most one scanner (combine multiple checks into one function
    if a plugin needs several)."""
    purge_scanners.register(owner, scanner)


def run_purge_scan(entity: CatalogEntity) -> list[PurgeReference]:
    """Run every registered scanner against `entity` (see `PurgeScannerRegistry.run`).

    Called by `EntityService.purge()`, inside the same transaction as the
    purge itself (entity-lifecycle-service spec: "purge's reference-scanning
    validation" runs in the delete transaction, not as a separate pre-check).
    """
    return purge_scanners.run(entity)
