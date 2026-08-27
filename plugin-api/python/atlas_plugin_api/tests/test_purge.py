"""Purge reference-scan extension point contract tests (`entity-removal-lifecycle`
spec: "Purge validation scans both FK-backed and ref-string-backed references").

No Django settings are configured in this package's own test environment
(see `test_kinds.py`'s equivalent guard) — `purge.py` needs none.
"""

import pytest

from atlas_plugin_api.purge import (
    DuplicatePurgeScannerError,
    PurgeReference,
    PurgeScannerRegistry,
)


def test_registry_runs_every_registered_scanner():
    registry = PurgeScannerRegistry()
    registry.register(
        "owner-a", lambda entity: [PurgeReference(label="a", active=True)]
    )
    registry.register(
        "owner-b", lambda entity: [PurgeReference(label="b", active=False)]
    )

    references = registry.run("some-entity")

    assert {ref.label for ref in references} == {"a", "b"}


def test_registry_rejects_a_duplicate_owner():
    registry = PurgeScannerRegistry()
    registry.register("owner-a", lambda entity: [])

    with pytest.raises(DuplicatePurgeScannerError):
        registry.register("owner-a", lambda entity: [])


def test_registry_with_no_scanners_returns_no_references():
    registry = PurgeScannerRegistry()

    assert registry.run("some-entity") == []


def test_purge_reference_defaults_to_no_cascade():
    reference = PurgeReference(label="thing", active=True)

    assert reference.cascade is None
