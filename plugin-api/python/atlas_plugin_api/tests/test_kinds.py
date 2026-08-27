"""Entity Kind registration contract tests.

No Django settings are configured in this package's own test environment
(`atlas_plugin_api` must stay importable without one — see
`test_descriptor.py`'s equivalent guard); `kinds.py` needs none, unlike
`catalog.py`'s `get_catalog_entity_model()`.
"""

import pytest

from atlas_plugin_api.kinds import (
    ARCHITECTURE_ACTOR_V1,
    ARCHITECTURE_SUBJECT_V1,
    SCHEMA_HOST_V1,
    DuplicateKindError,
    EntityKindHandler,
    EntityKindRegistry,
    Ok,
    Unavailable,
    ValidateDeleteError,
    entity_deprecated,
    register_kind,
    resolve_capability,
)


class _StubHandler:
    def __init__(self, kind_id, provides=(), deprecated=False):
        self.kind_id = kind_id
        self.spec_schema = None
        self.provides = list(provides)
        self._deprecated = deprecated

    def create_details(self, entity, spec):
        pass

    def update_details(self, entity, spec):
        pass

    def serialize_details(self, entity):
        pass

    def validate_delete(self, entity):
        pass

    def is_deprecated(self, entity):
        return self._deprecated


def test_stub_handler_satisfies_the_published_protocol():
    assert isinstance(_StubHandler("system"), EntityKindHandler)


def test_register_kind_registers_against_the_process_wide_registry():
    from atlas_plugin_api.kinds import registry

    register_kind(_StubHandler("_test_register_kind"))

    assert registry.resolve("_test_register_kind") is not None
    registry._handlers.pop("_test_register_kind")
    registry._owners.pop("_test_register_kind")


def test_register_kind_rejects_a_duplicate_kind_id():
    registry = EntityKindRegistry()
    registry.register(_StubHandler("system"))

    with pytest.raises(DuplicateKindError) as exc_info:
        registry.register(_StubHandler("system"), owner="atlas.other")

    assert "system" in str(exc_info.value)


def test_resolve_capability_uses_the_process_wide_registry():
    from atlas_plugin_api.kinds import registry

    registry.register(
        _StubHandler("_test_resolve_capability", provides=[ARCHITECTURE_SUBJECT_V1]),
    )
    try:
        assert resolve_capability(
            "_test_resolve_capability", ARCHITECTURE_SUBJECT_V1
        ) == Ok(True)
        assert resolve_capability(
            "_test_resolve_capability", "no-such-capability"
        ) == Ok(False)
        assert (
            resolve_capability("does-not-exist", ARCHITECTURE_SUBJECT_V1)
            == Unavailable()
        )
    finally:
        registry._handlers.pop("_test_resolve_capability")
        registry._owners.pop("_test_resolve_capability")


def test_capability_constants():
    assert ARCHITECTURE_SUBJECT_V1 == "architecture.subject.v1"
    assert ARCHITECTURE_ACTOR_V1 == "architecture.actor.v1"
    assert SCHEMA_HOST_V1 == "schema.host.v1"


def test_validate_delete_error_is_a_plain_exception():
    with pytest.raises(ValidateDeleteError):
        raise ValidateDeleteError("cannot delete")


def test_kinds_module_is_importable_without_django_setup():
    import atlas_plugin_api.kinds  # noqa: F401


class _Entity:
    """Duck-typed stand-in for `CatalogEntity` — only `.kind` is needed."""

    def __init__(self, kind):
        self.kind = kind


def test_entity_deprecated_delegates_to_the_registered_handler():
    from atlas_plugin_api.kinds import registry

    registry.register(_StubHandler("_test_entity_deprecated", deprecated=True))
    try:
        assert entity_deprecated(_Entity("_test_entity_deprecated")) is True
    finally:
        registry._handlers.pop("_test_entity_deprecated")
        registry._owners.pop("_test_entity_deprecated")


def test_entity_deprecated_is_false_for_an_unregistered_kind():
    assert entity_deprecated(_Entity("_no_such_kind")) is False
