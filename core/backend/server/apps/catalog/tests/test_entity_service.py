"""Core Entity Service tests."""

import pytest

from server.apps.catalog.api.schemas import MetadataIn
from server.apps.catalog.kinds import ValidateDeleteError
from server.apps.catalog.kinds.registry import EntityKindRegistry
from server.apps.catalog.models import (
    KIND_SYSTEM,
    CatalogEntity,
    EntityAuditRecord,
)
from server.apps.catalog.services.entity_service import (
    EntityNotFoundError,
    EntityService,
    EntityUnavailableError,
    UnknownEntityKindError,
)
from server.apps.catalog.tests.factories import create_system

pytestmark = pytest.mark.django_db


class _FailingHandler:
    """A handler whose `create_details` always raises, for rollback tests."""

    kind_id = KIND_SYSTEM
    spec_schema = None

    def create_details(self, entity, spec):
        raise RuntimeError("boom")

    def update_details(self, entity, spec):
        raise AssertionError("not exercised")

    def serialize_details(self, entity):
        raise AssertionError("not exercised")

    def validate_delete(self, entity):
        raise AssertionError("not exercised")


def test_kind_handler_failure_rolls_back_the_whole_create(
    group, superuser_account
):
    registry = EntityKindRegistry()
    registry.register(_FailingHandler())
    service = EntityService(registry=registry)

    with pytest.raises(RuntimeError):
        service.create(
            kind_id=KIND_SYSTEM,
            owner_ref="group:platform",
            metadata=MetadataIn(name="rollback-system"),
            spec=object(),
            actor=superuser_account,
        )

    assert not CatalogEntity.objects.filter(
        kind=KIND_SYSTEM, name="rollback-system"
    ).exists()
    assert not EntityAuditRecord.objects.filter(kind=KIND_SYSTEM).exists()


def test_create_unknown_kind_raises_a_distinguishable_error(
    group, superuser_account
):
    service = EntityService(registry=EntityKindRegistry())

    with pytest.raises(UnknownEntityKindError):
        service.create(
            kind_id="does-not-exist",
            owner_ref="group:platform",
            metadata=MetadataIn(name="whatever"),
            spec=object(),
            actor=superuser_account,
        )


def test_update_of_a_missing_entity_raises_entity_not_found(superuser_account):
    service = EntityService()

    with pytest.raises(EntityNotFoundError):
        service.update(
            entity_id="00000000-0000-0000-0000-000000000000",
            actor=superuser_account,
        )


def test_successful_create_writes_entity_details_and_audit_atomically(
    owner_client, group
):
    response = owner_client.post(
        "/api/systems/",
        {
            "metadata": {"name": "audited-system"},
            "spec": {"owner": "group:platform"},
        },
    )
    assert response.status_code == 201
    entity_id = response.json()["id"]

    assert CatalogEntity.objects.filter(pk=entity_id, kind=KIND_SYSTEM).exists()
    record = EntityAuditRecord.objects.get(
        kind=KIND_SYSTEM, entity_id=entity_id
    )
    assert record.action == EntityAuditRecord.ACTION_CREATE
    assert record.diff["metadata"]["name"] == "audited-system"


def test_update_writes_an_audit_record(owner_client, system):
    response = owner_client.patch(
        f"/api/systems/{system.id}/", {"metadata": {"title": "Updated"}}
    )
    assert response.status_code == 200

    record = EntityAuditRecord.objects.get(
        entity_id=system.id, action=EntityAuditRecord.ACTION_UPDATE
    )
    assert record.diff["metadata"] == {"title": "Updated"}


def test_delete_route_is_retired_for_lifecycle_kinds(
    owner_client, system, component, resource, api
):
    """Plain Delete is retired for System/Component/Resource/API —
    Remove then Purge is the only remaining path to
    permanently destroying one of these four kinds."""
    for kind_path, entity in (
        ("systems", system),
        ("components", component),
        ("resources", resource),
        ("apis", api),
    ):
        response = owner_client.delete(f"/api/{kind_path}/{entity.id}/")
        assert response.status_code == 405
        assert CatalogEntity.objects.filter(pk=entity.id).exists()


def test_deleting_a_group_with_an_active_owned_entity_is_blocked(
    group,
    superuser_account,
):
    system = create_system(name="owned-system", owner=group)

    with pytest.raises(ValidateDeleteError):
        EntityService().delete(entity_id=group.id, actor=superuser_account)

    assert CatalogEntity.objects.filter(pk=group.id).exists()
    system.refresh_from_db()
    assert system.owner_id == group.id


def test_deleting_a_group_whose_owned_entities_are_all_removed_succeeds(
    group,
    superuser_account,
):
    system = create_system(name="owned-system", owner=group)
    EntityService().remove(entity_id=system.id, actor=superuser_account)

    EntityService().delete(entity_id=group.id, actor=superuser_account)

    assert not CatalogEntity.objects.filter(pk=group.id).exists()
    system.refresh_from_db()
    assert system.owner_id is None


def test_get_of_a_missing_entity_raises_entity_not_found():
    service = EntityService()

    with pytest.raises(EntityNotFoundError):
        service.get("00000000-0000-0000-0000-000000000000")


def test_get_with_a_registered_handler_returns_the_serialized_spec(system):
    read = EntityService().get(system.id)

    assert read.entity == system
    assert read.unavailable is False
    assert read.spec is not None


def test_get_with_no_registered_handler_returns_an_unavailable_read(system):
    service = EntityService(registry=EntityKindRegistry())

    read = service.get(system.id)

    assert read.entity == system
    assert read.spec is None
    assert read.unavailable is True


def test_list_mixes_available_and_unavailable_reads(system, resource):
    from server.apps.catalog.kinds.registry import registry as default_registry

    registry = EntityKindRegistry()
    registry.register(default_registry.resolve(KIND_SYSTEM))
    service = EntityService(registry=registry)

    reads = {read.entity.id: read for read in service.list()}

    assert reads[system.id].unavailable is False
    assert reads[resource.id].unavailable is True
    assert reads[resource.id].spec is None


def test_list_filters_by_kind(system, resource):
    reads = EntityService().list(kind_id=KIND_SYSTEM)

    assert {read.entity.id for read in reads} == {system.id}


def test_update_of_an_unavailable_entity_is_rejected(system, superuser_account):
    service = EntityService(registry=EntityKindRegistry())

    with pytest.raises(EntityUnavailableError):
        service.update(
            entity_id=system.id,
            metadata=MetadataIn(name="renamed"),
            actor=superuser_account,
        )

    system.refresh_from_db()
    assert system.name == "user-management"


def test_delete_of_an_unavailable_entity_is_rejected(system, superuser_account):
    service = EntityService(registry=EntityKindRegistry())

    with pytest.raises(EntityUnavailableError):
        service.delete(entity_id=system.id, actor=superuser_account)

    assert CatalogEntity.objects.filter(pk=system.id).exists()


def _create_system_via_api(client, name):
    return client.post(
        "/api/systems/",
        {"metadata": {"name": name}, "spec": {"owner": "group:platform"}},
    )


def test_creating_a_duplicate_name_is_a_client_error_not_a_server_error(
    owner_client, group
):
    assert _create_system_via_api(owner_client, "ledger").status_code == 201

    # Names are unique per kind regardless of case.
    for name in ("ledger", "LEDGER"):
        response = _create_system_via_api(owner_client, name)

        assert response.status_code == 400
        assert "already exists" in str(response.json())
    assert CatalogEntity.objects.filter(name__iexact="ledger").count() == 1
    assert (
        EntityAuditRecord.objects.filter(action=EntityAuditRecord.ACTION_CREATE)
        .filter(diff__metadata__name__iexact="ledger")
        .count()
        == 1
    )


def test_the_same_name_is_allowed_for_a_different_kind(owner_client, group):
    assert _create_system_via_api(owner_client, "ledger").status_code == 201

    response = owner_client.post(
        "/api/resources/",
        {
            "metadata": {"name": "ledger"},
            "spec": {"type": "database", "owner": "group:platform"},
        },
    )

    assert response.status_code == 201


def test_renaming_onto_an_existing_name_is_rejected(owner_client, group):
    taken = _create_system_via_api(owner_client, "taken")
    other = _create_system_via_api(owner_client, "other")
    assert taken.status_code == other.status_code == 201

    response = owner_client.patch(
        f"/api/systems/{other.json()['id']}/", {"metadata": {"name": "Taken"}}
    )

    assert response.status_code == 400
    assert CatalogEntity.objects.get(pk=other.json()["id"]).name == "other"


def test_a_duplicate_name_does_not_mark_the_plugin_degraded(
    owner_client, group
):
    from server.apps.plugins.health import plugin_health, reset_degraded

    reset_degraded()
    _create_system_via_api(owner_client, "ledger")
    _create_system_via_api(owner_client, "ledger")

    assert {item.status for item in plugin_health()} <= {"active", "disabled"}
