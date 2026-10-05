"""Remove/Revive/Purge Entity Service transaction tests
(entity-removal-lifecycle spec: "Purge is a new, explicit action reachable
only from Removed", "Purge
validation scans both FK-backed and ref-string-backed references"), plus the
catalog-auth Purge Grant permission integration and the Remove/Revive/Purge
REST surface.
"""

import pytest
from atlas_plugin_flows.models import Flow
from atlas_plugin_ingestion.claims import claim_entity
from dmr.response import APIError

from server.apps.catalog.kinds import ValidateDeleteError
from server.apps.catalog.models import (
    CatalogEntity,
    EntityAuditRecord,
    PurgeGrant,
)
from server.apps.catalog.services.entity_service import EntityService
from server.apps.catalog.tests.factories import create_component, create_system

pytestmark = pytest.mark.django_db


# --- Remove / Revive (service-level) ----------------------------------------


def test_remove_sets_status_and_writes_an_audit_record(
    system, superuser_account
):
    EntityService().remove(entity_id=system.id, actor=superuser_account)

    system.refresh_from_db()
    assert system.status == CatalogEntity.STATUS_REMOVED
    record = EntityAuditRecord.objects.get(
        entity_id=system.id, action=EntityAuditRecord.ACTION_REMOVE
    )
    assert record.diff == {"status": CatalogEntity.STATUS_REMOVED}


def test_manual_remove_is_blocked_for_a_yaml_managed_entity(
    group, superuser_account
):
    from atlas_plugin_ingestion.models import RegisteredRepository

    repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/repo"
    )
    managed = create_system(
        name="managed",
        owner=group,
        source_kind="yaml",
    )
    claim_entity(managed, repo)

    with pytest.raises(APIError):
        EntityService().remove(entity_id=managed.id, actor=superuser_account)

    managed.refresh_from_db()
    assert managed.status == CatalogEntity.STATUS_ACTIVE


def test_revive_sets_status_back_to_active(system, superuser_account):
    EntityService().remove(entity_id=system.id, actor=superuser_account)

    EntityService().revive(entity_id=system.id, actor=superuser_account)

    system.refresh_from_db()
    assert system.status == CatalogEntity.STATUS_ACTIVE
    record = EntityAuditRecord.objects.get(
        entity_id=system.id, action=EntityAuditRecord.ACTION_REVIVE
    )
    assert record.diff == {"status": CatalogEntity.STATUS_ACTIVE}


def test_manual_revive_is_blocked_for_a_yaml_managed_entity(
    group, superuser_account
):
    from atlas_plugin_ingestion.models import RegisteredRepository

    repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/repo"
    )
    managed = create_system(
        name="managed",
        owner=group,
        source_kind="yaml",
    )
    claim_entity(managed, repo)
    EntityService().remove(
        entity_id=managed.id,
        actor=superuser_account,
        source=CatalogEntity.SOURCE_YAML,
    )

    with pytest.raises(APIError):
        EntityService().revive(entity_id=managed.id, actor=superuser_account)

    managed.refresh_from_db()
    assert managed.status == CatalogEntity.STATUS_REMOVED


# --- Purge: state machine / permission ---------------------------------------


def test_purge_is_rejected_on_an_active_entity(system, superuser_account):
    with pytest.raises(ValidateDeleteError):
        EntityService().purge(entity_id=system.id, actor=superuser_account)

    assert CatalogEntity.objects.filter(pk=system.id).exists()


def test_purge_requires_a_purge_grant_not_just_owner_group_membership(
    system, owner_user, owner_account
):
    EntityService().remove(entity_id=system.id, actor=owner_account)

    with pytest.raises(APIError):
        EntityService().purge(entity_id=system.id, actor=owner_account)

    assert CatalogEntity.objects.filter(pk=system.id).exists()


def test_purge_grant_holder_purges_a_removed_entity_with_no_references(
    system, group, owner_user, owner_account
):
    EntityService().remove(entity_id=system.id, actor=owner_account)
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    EntityService().purge(entity_id=system.id, actor=owner_account)

    assert not CatalogEntity.objects.filter(pk=system.id).exists()
    record = EntityAuditRecord.objects.get(
        entity_id=system.id, action=EntityAuditRecord.ACTION_PURGE
    )
    assert record.diff == {
        "name": "user-management",
        "namespace": system.namespace,
    }


def test_global_admin_purges_without_a_grant(system, superuser_account):
    EntityService().remove(entity_id=system.id, actor=superuser_account)

    EntityService().purge(entity_id=system.id, actor=superuser_account)

    assert not CatalogEntity.objects.filter(pk=system.id).exists()


def test_purge_grant_holder_purges_yaml_entity_despite_manual_write_block(
    group, owner_account
):
    from atlas_plugin_ingestion.models import RegisteredRepository

    repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/repo"
    )
    managed = create_system(
        name="managed",
        owner=group,
        source_kind="yaml",
    )
    claim_entity(managed, repo)
    EntityService().remove(
        entity_id=managed.id,
        actor=owner_account,
        source=CatalogEntity.SOURCE_YAML,
    )
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    EntityService().purge(entity_id=managed.id, actor=owner_account)

    assert not CatalogEntity.objects.filter(pk=managed.id).exists()


def test_purged_name_is_claimable_by_a_new_entity_with_a_new_id(
    group, owner_user, owner_account
):
    original = create_system(name="checkout", owner=group)
    original_id = original.id
    EntityService().remove(entity_id=original.id, actor=owner_account)
    PurgeGrant.objects.create(group=group, grantee=owner_account)
    EntityService().purge(entity_id=original.id, actor=owner_account)

    recreated = create_system(name="checkout", owner=group)

    assert recreated.id != original_id
    assert not CatalogEntity.objects.filter(pk=original_id).exists()


# --- Purge: reference scanning (FK-backed) -----------------------------------


def test_purge_blocked_by_an_active_component_depends_on(
    group, system, resource, owner_user, owner_account
):
    create_component(
        name="checkout-service",
        owner=group,
        system=system,
        depends_on=[resource],
    )
    EntityService().remove(entity_id=resource.id, actor=owner_account)
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    with pytest.raises(ValidateDeleteError) as exc_info:
        EntityService().purge(entity_id=resource.id, actor=owner_account)

    assert "checkout-service" in str(exc_info.value)
    assert CatalogEntity.objects.filter(pk=resource.id).exists()


def test_purge_cascades_a_removed_components_depends_on_link(
    group, system, resource, owner_user, owner_account
):
    dependent = create_component(
        name="checkout-service",
        owner=group,
        system=system,
        depends_on=[resource],
    )
    EntityService().remove(entity_id=resource.id, actor=owner_account)
    EntityService().remove(entity_id=dependent.id, actor=owner_account)
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    EntityService().purge(entity_id=resource.id, actor=owner_account)

    assert not CatalogEntity.objects.filter(pk=resource.id).exists()
    assert not dependent.component_details.depends_on.filter(
        pk=resource.id
    ).exists()


def test_purge_blocked_by_an_active_component_providing_the_api(
    group, system, api, owner_user, owner_account
):
    create_component(
        name="checkout-service", owner=group, system=system, provides_apis=[api]
    )
    EntityService().remove(entity_id=api.id, actor=owner_account)
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    with pytest.raises(ValidateDeleteError) as exc_info:
        EntityService().purge(entity_id=api.id, actor=owner_account)

    assert "checkout-service" in str(exc_info.value)
    assert CatalogEntity.objects.filter(pk=api.id).exists()


def test_purge_succeeds_when_all_references_are_already_removed(
    group, system, api, owner_user, owner_account
):
    dependent = create_component(
        name="checkout-service", owner=group, system=system, consumes_apis=[api]
    )
    EntityService().remove(entity_id=api.id, actor=owner_account)
    EntityService().remove(entity_id=dependent.id, actor=owner_account)
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    EntityService().purge(entity_id=api.id, actor=owner_account)

    assert not CatalogEntity.objects.filter(pk=api.id).exists()


def test_purge_succeeds_trivially_when_nothing_ever_referenced_the_entity(
    group, resource, owner_user, owner_account
):
    EntityService().remove(entity_id=resource.id, actor=owner_account)
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    EntityService().purge(entity_id=resource.id, actor=owner_account)

    assert not CatalogEntity.objects.filter(pk=resource.id).exists()


# --- Purge: reference scanning (ref-string-backed, Flow entity_ref) ---------


def test_purge_blocked_by_an_active_flow_entity_ref(
    group, system, component, owner_user, owner_account
):
    flow = Flow.objects.create(
        system=system,
        name="checkout-flow",
        steps=[{"id": "call-service", "entity_ref": component.ref}],
    )
    EntityService().remove(entity_id=component.id, actor=owner_account)
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    with pytest.raises(ValidateDeleteError) as exc_info:
        EntityService().purge(entity_id=component.id, actor=owner_account)

    assert flow.name in str(exc_info.value)
    assert CatalogEntity.objects.filter(pk=component.id).exists()


# --- Remove/Revive/Purge REST surface ----------------------------------------


def test_owner_removes_revives_and_purges_a_system_via_rest(
    owner_client, group, superuser_account
):
    system = create_system(name="decommissioned", owner=group)

    remove_response = owner_client.post(f"/api/systems/{system.id}/remove/")
    assert remove_response.status_code == 200
    system.refresh_from_db()
    assert system.status == CatalogEntity.STATUS_REMOVED

    revive_response = owner_client.post(f"/api/systems/{system.id}/revive/")
    assert revive_response.status_code == 200
    system.refresh_from_db()
    assert system.status == CatalogEntity.STATUS_ACTIVE

    owner_client.post(f"/api/systems/{system.id}/remove/")
    PurgeGrant.objects.create(group=group, grantee=superuser_account)
    purge_response = owner_client.post(f"/api/systems/{system.id}/purge/")
    assert (
        purge_response.status_code == 403
    )  # owner_client's user holds no Purge Grant


def test_purge_grant_holder_purges_a_component_via_rest(
    owner_client, owner_account, group, component
):
    owner_client.post(f"/api/components/{component.id}/remove/")
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    response = owner_client.post(f"/api/components/{component.id}/purge/")

    assert response.status_code == 204
    assert not CatalogEntity.objects.filter(pk=component.id).exists()


def test_purge_grant_holder_purges_a_resource_via_rest(
    owner_client, owner_account, group, resource
):
    owner_client.post(f"/api/resources/{resource.id}/remove/")
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    response = owner_client.post(f"/api/resources/{resource.id}/purge/")

    assert response.status_code == 204
    assert not CatalogEntity.objects.filter(pk=resource.id).exists()


def test_purge_grant_holder_purges_an_api_via_rest(
    owner_client, owner_account, group, api
):
    owner_client.post(f"/api/apis/{api.id}/remove/")
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    response = owner_client.post(f"/api/apis/{api.id}/purge/")

    assert response.status_code == 204
    assert not CatalogEntity.objects.filter(pk=api.id).exists()


def test_purge_via_rest_is_rejected_on_an_active_entity(
    owner_client, owner_account, group, resource
):
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    response = owner_client.post(f"/api/resources/{resource.id}/purge/")

    assert response.status_code == 400
    assert CatalogEntity.objects.filter(pk=resource.id).exists()


# --- Entity detail/list surface entity status


def test_entity_detail_reports_its_status(owner_client, system):
    active_response = owner_client.get(f"/api/systems/{system.id}/")
    assert active_response.json()["status"] == "active"

    owner_client.post(f"/api/systems/{system.id}/remove/")

    removed_response = owner_client.get(f"/api/systems/{system.id}/")
    assert removed_response.json()["status"] == "removed"


# --- List filtering: removed entities hidden by default, ungated toggle -------


def test_default_list_excludes_removed_entities(owner_client, group):
    active = create_system(name="active-system", owner=group)
    removed = create_system(name="removed-system", owner=group)
    owner_client.post(f"/api/systems/{removed.id}/remove/")

    response = owner_client.get("/api/systems/")

    names = {
        item["metadata"]["name"]
        for item in response.json()["page"]["objectList"]
    }
    assert active.name in names
    assert removed.name not in names


def test_status_all_reveals_removed_entities_to_any_authenticated_viewer(
    other_client, group
):
    removed = create_system(name="removed-system", owner=group)
    EntityService().remove(
        entity_id=removed.id, actor=None, source=CatalogEntity.SOURCE_YAML
    )

    response = other_client.get("/api/systems/", {"status": "all"})

    names = {
        item["metadata"]["name"]
        for item in response.json()["page"]["objectList"]
    }
    assert removed.name in names


# --- History (entity-removal-lifecycle spec: "audited and visible on a
# History tab") ---


def test_history_reports_remove_then_revive_with_actor_and_timestamp(
    owner_client, owner_user, system
):
    owner_client.post(f"/api/systems/{system.id}/remove/")
    owner_client.post(f"/api/systems/{system.id}/revive/")

    response = owner_client.get(f"/api/systems/{system.id}/history/")

    assert response.status_code == 200
    actions = [record["action"] for record in response.json()]
    assert actions[:2] == ["revive", "remove"]  # newest first
    for record in response.json()[:2]:
        assert record["actor"]
        assert record["timestamp"]


def test_history_reports_no_actor_for_an_ingestion_triggered_action(group):
    from atlas_plugin_ingestion.models import RegisteredRepository

    repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/repo"
    )
    managed = create_system(
        name="managed",
        owner=group,
        source_kind="yaml",
    )
    claim_entity(managed, repo)
    EntityService().remove(
        entity_id=managed.id, actor=None, source=CatalogEntity.SOURCE_YAML
    )

    record = EntityAuditRecord.objects.get(
        entity_id=managed.id, action=EntityAuditRecord.ACTION_REMOVE
    )
    assert record.actor is None
