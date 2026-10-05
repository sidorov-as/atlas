"""Entity read/write contract tests.

No Django settings are configured in this package's own test environment
(`atlas_plugin_api` must stay importable without one — see
`test_descriptor.py`'s equivalent guard); `entity_service.py` needs none,
unlike `catalog.py`'s `get_catalog_entity_model()`.
"""

import pytest

from atlas_plugin_api.entity_service import (
    EntityNotFoundError,
    EntityRead,
    EntityService,
    EntityUnavailableError,
    UnknownEntityKindError,
    bind_entity_service,
    get_entity_service,
)


class _StubEntityService:
    def get(self, entity_id):
        return EntityRead(entity=None, spec=None, unavailable=False)

    def list(self, *, kind_id=None):
        return []

    def create(
        self,
        *,
        kind_id,
        owner_ref=None,
        metadata,
        spec,
        actor,
        source="manual",
    ):
        return None

    def update(
        self,
        *,
        entity_id,
        owner_ref=None,
        metadata=None,
        spec=None,
        actor,
        source="manual",
    ):
        return None

    def delete(self, *, entity_id, actor):
        pass

    def remove(self, *, entity_id, actor, source="manual"):
        return None

    def revive(self, *, entity_id, actor, source="manual"):
        return None

    def purge(self, *, entity_id, actor):
        pass


@pytest.fixture(autouse=True)
def _reset_bound_entity_service():
    import atlas_plugin_api.entity_service as module

    previous = module._entity_service
    try:
        yield
    finally:
        module._entity_service = previous


def test_stub_service_satisfies_the_published_protocol():
    assert isinstance(_StubEntityService(), EntityService)


def test_get_entity_service_raises_before_binding():
    import atlas_plugin_api.entity_service as module

    module._entity_service = None

    with pytest.raises(RuntimeError):
        get_entity_service()


def test_bind_entity_service_registers_the_singleton():
    service = _StubEntityService()

    bind_entity_service(service)

    assert get_entity_service() is service


def test_entity_read_is_a_plain_frozen_dataclass():
    read = EntityRead(entity="e", spec=None, unavailable=True)
    assert read.entity == "e"
    assert read.unavailable is True


def test_entity_unavailable_error_is_an_unknown_entity_kind_error():
    exc = EntityUnavailableError("system")
    assert isinstance(exc, UnknownEntityKindError)
    assert exc.kind_id == "system"


def test_entity_not_found_error_is_a_plain_exception():
    with pytest.raises(EntityNotFoundError):
        raise EntityNotFoundError("nope")


def test_entity_service_module_is_importable_without_django_setup():
    import atlas_plugin_api.entity_service  # noqa: F401
