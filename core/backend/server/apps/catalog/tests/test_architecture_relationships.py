"""Manual Architecture Relationship API coverage."""

import pytest

from server.apps.catalog.models import ArchitectureRelationship

pytestmark = pytest.mark.django_db


def _create_payload(component, target, **overrides):
    payload = {
        "source": component.ref,
        "target": target.ref,
        "label": "Makes API calls to",
        "technology": "REST/HTTPS",
        "interactionKind": "synchronous",
        "tags": ["runtime"],
    }
    payload.update(overrides)
    return payload


def test_owner_can_create_list_update_and_delete_manual_relationship(
    owner_client, component, api
):
    created = owner_client.post(
        "/api/architecture-relationships/", _create_payload(component, api)
    )
    assert created.status_code == 201
    relationship = created.json()
    assert relationship == {
        "id": relationship["id"],
        "source": component.ref,
        "sourceKind": "component",
        "sourceId": str(component.id),
        "sourceStatus": "active",
        "sourceDeprecated": False,
        "target": api.ref,
        "targetKind": "api",
        "targetId": str(api.id),
        "targetStatus": "active",
        "targetDeprecated": False,
        "label": "Makes API calls to",
        "technology": "REST/HTTPS",
        "interactionKind": "synchronous",
        "tags": ["runtime"],
        "origin": "manual",
    }

    listed = owner_client.get(
        "/api/architecture-relationships/", {"source": component.ref}
    )
    assert listed.status_code == 200
    assert listed.json() == [relationship]

    updated = owner_client.patch(
        f"/api/architecture-relationships/{relationship['id']}/",
        {"label": "Calls public API", "interactionKind": "manual"},
    )
    assert updated.status_code == 200
    assert updated.json()["label"] == "Calls public API"
    assert updated.json()["interactionKind"] == "manual"

    deleted = owner_client.delete(
        f"/api/architecture-relationships/{relationship['id']}/"
    )
    assert deleted.status_code == 204
    assert not ArchitectureRelationship.objects.filter(
        pk=relationship["id"]
    ).exists()


def test_list_includes_canonical_incoming_and_outgoing_relationships(
    owner_client,
    component,
    api,
    resource,
):
    outgoing = ArchitectureRelationship.objects.create(
        source=component,
        target=api,
        label="Calls API",
    )
    incoming = ArchitectureRelationship.objects.create(
        source=resource,
        target=component,
        label="Provides data to",
        origin="yaml",
    )

    response = owner_client.get(
        "/api/architecture-relationships/", {"source": component.ref}
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": outgoing.id,
            "source": component.ref,
            "sourceKind": "component",
            "sourceId": str(component.id),
            "sourceStatus": "active",
            "sourceDeprecated": False,
            "target": api.ref,
            "targetKind": "api",
            "targetId": str(api.id),
            "targetStatus": "active",
            "targetDeprecated": False,
            "label": "Calls API",
            "technology": "",
            "interactionKind": "manual",
            "tags": [],
            "origin": "manual",
        },
        {
            "id": incoming.id,
            "source": resource.ref,
            "sourceKind": "resource",
            "sourceId": str(resource.id),
            "sourceStatus": "active",
            "sourceDeprecated": False,
            "target": component.ref,
            "targetKind": "component",
            "targetId": str(component.id),
            "targetStatus": "active",
            "targetDeprecated": False,
            "label": "Provides data to",
            "technology": "",
            "interactionKind": "manual",
            "tags": [],
            "origin": "yaml",
        },
    ]


def test_removed_target_status_is_surfaced(owner_client, component, api):
    api.status = "removed"
    api.save(update_fields=["status"])
    relationship = ArchitectureRelationship.objects.create(
        source=component, target=api, label="Calls API"
    )

    response = owner_client.get(
        "/api/architecture-relationships/", {"source": component.ref}
    )

    assert response.status_code == 200
    [entry] = [row for row in response.json() if row["id"] == relationship.id]
    assert entry["targetStatus"] == "removed"
    assert entry["sourceStatus"] == "active"


def test_deprecated_target_flag_is_surfaced(
    owner_client, component, resource, group, system
):
    from server.apps.catalog.tests.factories import create_component

    deprecated_dependency = create_component(
        name="legacy-billing", owner=group, system=system
    )
    deprecated_dependency.component_details.lifecycle = "deprecated"
    deprecated_dependency.component_details.save(update_fields=["lifecycle"])
    relationship = ArchitectureRelationship.objects.create(
        source=component,
        target=deprecated_dependency,
        label="Calls legacy service",
    )

    response = owner_client.get(
        "/api/architecture-relationships/", {"source": component.ref}
    )

    assert response.status_code == 200
    [entry] = [row for row in response.json() if row["id"] == relationship.id]
    assert entry["targetDeprecated"] is True


def test_non_owner_cannot_create_or_edit_manual_relationship(
    other_client,
    owner_client,
    owner_user,
    other_user,
    component,
    api,
):
    other_client.force_login(other_user.actor_details.account)
    response = other_client.post(
        "/api/architecture-relationships/", _create_payload(component, api)
    )
    assert response.status_code == 403

    owner_client.force_login(owner_user.actor_details.account)
    relationship = owner_client.post(
        "/api/architecture-relationships/",
        _create_payload(component, api),
    ).json()
    other_client.force_login(other_user.actor_details.account)
    response = other_client.patch(
        f"/api/architecture-relationships/{relationship['id']}/",
        {"label": "Hijacked"},
    )
    assert response.status_code == 403


def test_yaml_managed_source_and_yaml_relationship_are_read_only(
    owner_client, component, api, group
):
    component.source_kind = "yaml"
    component.save(update_fields=["source_kind"])
    create = owner_client.post(
        "/api/architecture-relationships/", _create_payload(component, api)
    )
    assert create.status_code == 403

    relationship = ArchitectureRelationship.objects.create(
        source=component,
        target=api,
        label="Declared relationship",
        origin="yaml",
    )
    assert (
        owner_client.patch(
            f"/api/architecture-relationships/{relationship.id}/",
            {"label": "Edited"},
        ).status_code
        == 403
    )
    assert (
        owner_client.delete(
            f"/api/architecture-relationships/{relationship.id}/"
        ).status_code
        == 403
    )
    relationship.refresh_from_db()
    assert relationship.label == "Declared relationship"


def test_target_accepts_user_and_group_actor_refs(
    owner_client, component, owner_user, group
):
    user_target = owner_client.post(
        "/api/architecture-relationships/",
        _create_payload(component, owner_user, label="Notifies"),
    )
    assert user_target.status_code == 201
    assert user_target.json()["targetKind"] == "user"
    assert user_target.json()["target"] == owner_user.ref

    group_target = owner_client.post(
        "/api/architecture-relationships/",
        _create_payload(component, group, label="Notifies team"),
    )
    assert group_target.status_code == 201
    assert group_target.json()["targetKind"] == "group"
    assert group_target.json()["target"] == group.ref


def test_relationship_validation_rejects_unknown_target_and_non_entity_source(
    owner_client, component, api, group
):
    invalid_target_payload = _create_payload(component, api)
    invalid_target_payload["target"] = "component:missing"
    invalid_target = owner_client.post(
        "/api/architecture-relationships/",
        invalid_target_payload,
    )
    assert invalid_target.status_code == 400

    invalid_source_payload = _create_payload(component, api)
    invalid_source_payload["source"] = group.ref
    invalid_source = owner_client.post(
        "/api/architecture-relationships/", invalid_source_payload
    )
    assert invalid_source.status_code == 400


def test_derived_relation_recompute_does_not_modify_architecture_relationship(
    owner_client,
    component,
    resource,
    api,
):
    created = owner_client.post(
        "/api/architecture-relationships/", _create_payload(component, api)
    )
    relationship_id = created.json()["id"]

    component.component_details.depends_on.add(resource)
    component.component_details.depends_on.clear()

    relationship = ArchitectureRelationship.objects.get(pk=relationship_id)
    assert relationship.source_id == component.id
    assert relationship.target_id == api.id
    assert relationship.label == "Makes API calls to"
