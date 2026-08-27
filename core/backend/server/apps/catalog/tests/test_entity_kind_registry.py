"""Entity Kind registry tests."""

import pytest

from server.apps.catalog.kinds.capability_result import Ok, Unavailable
from server.apps.catalog.kinds.registry import (
    DuplicateKindError,
    EntityKindRegistry,
)


def test_core_registry_is_the_published_contract_registry():
    # `server.apps.catalog.kinds.registry` re-exports `atlas_plugin_api.kinds`
    # same object, not a copy,
    # so a plugin registering via `atlas_plugin_api.register_kind()` and Core's
    # Entity Service resolving handlers both see the one process-wide registry.
    import atlas_plugin_api

    from server.apps.catalog.kinds import registry as core_registry

    assert core_registry is atlas_plugin_api.registry


class _StubHandler:
    def __init__(self, kind_id, provides=()):
        self.kind_id = kind_id
        self.spec_schema = None
        self.provides = list(provides)

    def create_details(self, entity, spec):
        pass

    def update_details(self, entity, spec):
        pass

    def serialize_details(self, entity):
        pass

    def validate_delete(self, entity):
        pass


def test_registering_a_kind_handler_makes_it_resolvable():
    registry = EntityKindRegistry()
    handler = _StubHandler("system")

    registry.register(handler)

    assert registry.resolve("system") is handler


def test_duplicate_kind_registration_is_rejected():
    registry = EntityKindRegistry()
    registry.register(_StubHandler("system"))

    with pytest.raises(DuplicateKindError) as exc_info:
        registry.register(_StubHandler("system"))

    assert "system" in str(exc_info.value)
    # The first registration must survive a rejected second attempt.
    assert isinstance(registry.resolve("system"), _StubHandler)


def test_unknown_kind_lookup_returns_a_distinguishable_not_found_result():
    registry = EntityKindRegistry()

    assert registry.resolve("does-not-exist") is None


def test_registered_ids_lists_registered_kind_ids_sorted():
    registry = EntityKindRegistry()
    registry.register(_StubHandler("system"))
    registry.register(_StubHandler("api"))

    assert registry.registered_ids() == ["api", "system"]


def test_default_registry_has_the_four_built_in_kinds_registered():
    from server.apps.catalog.kinds import registry
    from server.apps.catalog.models import (
        KIND_API,
        KIND_COMPONENT,
        KIND_RESOURCE,
        KIND_SYSTEM,
    )

    for kind_id in (KIND_SYSTEM, KIND_COMPONENT, KIND_RESOURCE, KIND_API):
        assert registry.resolve(kind_id) is not None


def test_capabilities_for_returns_the_handlers_declared_provides():
    registry = EntityKindRegistry()
    registry.register(
        _StubHandler("system", provides=["architecture.subject.v1"])
    )

    assert registry.capabilities_for("system") == ["architecture.subject.v1"]


def test_capabilities_for_an_unregistered_kind_is_empty():
    registry = EntityKindRegistry()

    assert registry.capabilities_for("does-not-exist") == []


def test_kind_ids_with_capability_lists_every_declaring_kind_sorted():
    registry = EntityKindRegistry()
    registry.register(
        _StubHandler("system", provides=["architecture.subject.v1"])
    )
    registry.register(
        _StubHandler("component", provides=["architecture.subject.v1"])
    )
    registry.register(_StubHandler("group", provides=["architecture.actor.v1"]))

    assert registry.kind_ids_with_capability("architecture.subject.v1") == [
        "component",
        "system",
    ]
    assert registry.kind_ids_with_capability("architecture.actor.v1") == [
        "group"
    ]
    assert registry.kind_ids_with_capability("no-such-capability") == []


def test_resolve_capability_distinguishes_absent_from_unavailable():
    registry = EntityKindRegistry()
    registry.register(
        _StubHandler("system", provides=["architecture.subject.v1"])
    )

    assert registry.resolve_capability(
        "system", "architecture.subject.v1"
    ) == Ok(True)
    assert registry.resolve_capability("system", "no-such-capability") == Ok(
        False
    )
    assert (
        registry.resolve_capability("does-not-exist", "architecture.subject.v1")
        == Unavailable()
    )


def test_default_registry_declares_expected_c4_capabilities():
    """`system`/`component` declare
    `architecture.subject.v1`; `group`/`user` (Actor) declare
    `architecture.actor.v1`; `resource`
    declares `schema.host.v1` (unconditionally,
    not scoped to `type=database` resources)."""
    from server.apps.catalog.kinds import (
        ARCHITECTURE_ACTOR_V1,
        ARCHITECTURE_SUBJECT_V1,
        SCHEMA_HOST_V1,
        registry,
    )
    from server.apps.catalog.models import (
        KIND_ACTOR,
        KIND_COMPONENT,
        KIND_GROUP,
        KIND_RESOURCE,
        KIND_SYSTEM,
    )

    for kind_id in (KIND_SYSTEM, KIND_COMPONENT):
        assert registry.capabilities_for(kind_id) == [ARCHITECTURE_SUBJECT_V1]
    for kind_id in (KIND_GROUP, KIND_ACTOR):
        assert registry.capabilities_for(kind_id) == [ARCHITECTURE_ACTOR_V1]
    assert registry.capabilities_for(KIND_RESOURCE) == [SCHEMA_HOST_V1]
