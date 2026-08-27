"""Capability registry tests (plugin-registries spec)."""

import pytest

from server.apps.catalog.kinds import Ok, Unavailable
from server.apps.plugins.capabilities import (
    CapabilityRegistry,
    DuplicateCapabilityError,
)


def test_registering_a_capability_makes_it_resolvable():
    registry = CapabilityRegistry()
    implementation = object()

    registry.register(
        "atlas.apis.operations.v1",
        implementation,
        owner="atlas.apis",
    )

    result = registry.resolve("atlas.apis.operations.v1")
    assert isinstance(result, Ok)
    assert result.value is implementation


def test_duplicate_capability_registration_is_rejected_and_names_both_plugins():
    registry = CapabilityRegistry()
    registry.register("atlas.apis.operations.v1", object(), owner="atlas.apis")

    with pytest.raises(DuplicateCapabilityError) as exc_info:
        registry.register(
            "atlas.apis.operations.v1",
            object(),
            owner="atlas.c4",
        )

    error = exc_info.value
    assert error.capability_id == "atlas.apis.operations.v1"
    assert error.existing_owner == "atlas.apis"
    assert error.new_owner == "atlas.c4"
    assert "atlas.apis" in str(error)
    assert "atlas.c4" in str(error)


def test_unknown_capability_lookup_returns_unavailable():
    registry = CapabilityRegistry()

    assert registry.resolve("does-not-exist") == Unavailable()


def test_registered_ids_lists_registered_capability_ids_sorted():
    registry = CapabilityRegistry()
    registry.register("atlas.b.v1", object(), owner="atlas.b")
    registry.register("atlas.a.v1", object(), owner="atlas.a")

    assert registry.registered_ids() == ["atlas.a.v1", "atlas.b.v1"]
