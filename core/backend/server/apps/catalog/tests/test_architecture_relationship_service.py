"""Core Architecture Relationship Service tests: origin, permission,
source-kind, and target-resolution rules, independent of the REST layer."""

import pytest
from atlas_plugin_api import (
    ArchitectureRelationshipNotFoundError,
    ArchitectureRelationshipReadOnlyError,
    ArchitectureRelationshipService,
    ArchitectureRelationshipSourceKindError,
    get_architecture_relationship_service,
)
from atlas_plugin_api.refs import RefError
from dmr.response import APIError

from server.apps.catalog.models import ArchitectureRelationship, Tag
from server.apps.catalog.services.architecture_relationship_service import (
    architecture_relationship_service as service,
)

pytestmark = [
    pytest.mark.django_db,
    # `owner_account` only owns `group` once its Actor is a member.
    pytest.mark.usefixtures("owner_user"),
]


def _create(actor, component, target, **overrides):
    kwargs = {
        "source_ref": component.ref,
        "target_ref": target.ref,
        "label": "Calls",
        "actor": actor,
    }
    kwargs.update(overrides)
    return service.create(**kwargs)


def test_service_is_bound_for_plugins():
    assert get_architecture_relationship_service() is service
    assert isinstance(service, ArchitectureRelationshipService)


def test_create_is_manual_origin_and_ensures_tags(
    owner_account, component, api
):
    relationship = _create(
        owner_account,
        component,
        api,
        technology="REST",
        interaction_kind="synchronous",
        tags=["runtime-tag"],
    )

    assert relationship.origin == "manual"
    assert relationship.source == component
    assert relationship.target == api
    assert relationship.technology == "REST"
    assert relationship.interaction_kind == "synchronous"
    assert Tag.objects.filter(name="runtime-tag").exists()


def test_create_requires_write_permission_on_source(
    other_account, component, api
):
    with pytest.raises(APIError) as exc:
        _create(other_account, component, api)

    assert exc.value.status_code == 403
    assert not ArchitectureRelationship.objects.exists()


def test_create_rejects_yaml_managed_source(owner_account, component, api):
    component.source_kind = "yaml"
    component.save(update_fields=["source_kind"])

    with pytest.raises(APIError) as exc:
        _create(owner_account, component, api)

    assert exc.value.status_code == 403


def test_create_rejects_non_writable_source_kind(owner_account, group, api):
    with pytest.raises(ArchitectureRelationshipSourceKindError):
        service.create(
            source_ref=group.ref,
            target_ref=api.ref,
            label="Calls",
            actor=owner_account,
        )


def test_create_rejects_unresolvable_target(owner_account, component):
    with pytest.raises(RefError):
        service.create(
            source_ref=component.ref,
            target_ref="component:missing",
            label="Calls",
            actor=owner_account,
        )

    assert not ArchitectureRelationship.objects.exists()


def test_create_rejects_unresolvable_source(owner_account, api):
    with pytest.raises(RefError):
        service.create(
            source_ref="component:missing",
            target_ref=api.ref,
            label="Calls",
            actor=owner_account,
        )


def test_update_changes_only_given_fields(
    owner_account, component, api, resource
):
    relationship = _create(
        owner_account, component, api, technology="REST", tags=["a"]
    )

    updated = service.update(
        relationship_id=relationship.id,
        fields={"label": "Reads from", "target": resource.ref},
        actor=owner_account,
    )

    assert updated.label == "Reads from"
    assert updated.target == resource
    assert updated.technology == "REST"
    assert updated.tags == ["a"]


def test_update_ensures_new_tags(owner_account, component, api):
    relationship = _create(owner_account, component, api)

    service.update(
        relationship_id=relationship.id,
        fields={"tags": ["fresh-tag"]},
        actor=owner_account,
    )

    assert Tag.objects.filter(name="fresh-tag").exists()


def test_update_and_delete_reject_yaml_origin(owner_account, component, api):
    relationship = ArchitectureRelationship.objects.create(
        source=component, target=api, label="Declared", origin="yaml"
    )

    with pytest.raises(ArchitectureRelationshipReadOnlyError):
        service.update(
            relationship_id=relationship.id,
            fields={"label": "Edited"},
            actor=owner_account,
        )
    with pytest.raises(ArchitectureRelationshipReadOnlyError):
        service.delete(relationship_id=relationship.id, actor=owner_account)

    relationship.refresh_from_db()
    assert relationship.label == "Declared"


def test_update_and_delete_require_write_permission(
    owner_account, other_account, component, api
):
    relationship = _create(owner_account, component, api)

    with pytest.raises(APIError) as exc:
        service.update(
            relationship_id=relationship.id,
            fields={"label": "Hijacked"},
            actor=other_account,
        )
    assert exc.value.status_code == 403
    with pytest.raises(APIError):
        service.delete(relationship_id=relationship.id, actor=other_account)

    assert ArchitectureRelationship.objects.filter(pk=relationship.id).exists()


def test_update_and_delete_unknown_id_are_not_found(owner_account):
    with pytest.raises(ArchitectureRelationshipNotFoundError):
        service.update(relationship_id=999999, fields={}, actor=owner_account)
    with pytest.raises(ArchitectureRelationshipNotFoundError):
        service.delete(relationship_id=999999, actor=owner_account)


def test_delete_removes_manual_relationship(owner_account, component, api):
    relationship = _create(owner_account, component, api)

    service.delete(relationship_id=relationship.id, actor=owner_account)

    assert not ArchitectureRelationship.objects.filter(
        pk=relationship.id
    ).exists()


def test_list_for_entity_returns_both_directions_with_origin(
    owner_account, component, api, resource
):
    outgoing = _create(owner_account, component, api)
    incoming = ArchitectureRelationship.objects.create(
        source=resource, target=component, label="Feeds", origin="yaml"
    )
    ArchitectureRelationship.objects.create(
        source=resource, target=api, label="Unrelated"
    )

    listed = service.list_for_entity(entity_ref=component.ref)

    assert [(r.id, r.origin) for r in listed] == [
        (outgoing.id, "manual"),
        (incoming.id, "yaml"),
    ]


def test_list_for_entity_rejects_unresolvable_ref():
    with pytest.raises(RefError):
        service.list_for_entity(entity_ref="component:missing")
