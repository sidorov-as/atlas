"""Django admin -> Entity Service routing tests (Team is a registered
Entity Kind; Django admin creation goes through the Entity Service).
"""

import pytest
from server.apps.catalog.models.audit import EntityAuditRecord

from atlas_plugin_standard_catalog.models import ActorDetails, GroupDetails

pytestmark = pytest.mark.django_db


def test_creating_a_team_via_admin_goes_through_the_entity_service(superuser_client):
    response = superuser_client.post(
        "/admin/catalog/groupdetails/add/",
        {
            "name": "platform-admin-created",
            "title": "Platform",
            "description": "Created via Django admin",
            "type": "team",
            "members": [],
        },
    )

    assert response.status_code == 302
    group_details = GroupDetails.objects.get(entity__name="platform-admin-created")
    assert group_details.type == "team"
    assert group_details.entity.title == "Platform"
    # Created through `EntityService.create`, not `GroupDetails.objects.create`
    # directly — an audit record is the observable proof.
    assert EntityAuditRecord.objects.filter(
        entity_id=group_details.entity_id,
        action=EntityAuditRecord.ACTION_CREATE,
    ).exists()


def test_editing_a_team_via_admin_goes_through_the_entity_service(
    superuser_client, group
):
    GroupDetails.objects.filter(entity=group).update(type="team")

    response = superuser_client.post(
        f"/admin/catalog/groupdetails/{group.pk}/change/",
        {
            "name": group.name,
            "title": "Renamed via admin",
            "description": "",
            "type": "business-unit",
            "members": [],
        },
    )

    assert response.status_code == 302
    group.refresh_from_db()
    assert group.title == "Renamed via admin"
    assert group.group_details.type == "business-unit"
    assert EntityAuditRecord.objects.filter(
        entity_id=group.pk,
        action=EntityAuditRecord.ACTION_UPDATE,
    ).exists()


def test_creating_an_actor_via_admin_goes_through_the_entity_service(superuser_client):
    response = superuser_client.post(
        "/admin/catalog/actordetails/add/",
        {
            "name": "jdoe",
            "title": "",
            "description": "",
            "display_name": "Jane Doe",
            "email": "jdoe@example.com",
            "account": "",
        },
    )

    assert response.status_code == 302
    actor_details = ActorDetails.objects.get(entity__name="jdoe")
    assert actor_details.display_name == "Jane Doe"
    assert actor_details.email == "jdoe@example.com"
    assert EntityAuditRecord.objects.filter(
        entity_id=actor_details.entity_id,
        action=EntityAuditRecord.ACTION_CREATE,
    ).exists()


def test_non_superuser_staff_cannot_create_a_team(client, django_user_model, group):
    """`EntityWritePermission` (permissions.py) requires a superuser for the
    ownerless Group/Actor kinds — a merely-staff account with model
    permissions still can't route around that at the Entity Service layer."""
    staff = django_user_model.objects.create_user(
        username="staff",
        password="password123",
        is_staff=True,
    )
    from django.contrib.auth.models import Permission

    staff.user_permissions.add(
        *Permission.objects.filter(codename__in=("add_groupdetails",))
    )
    client.force_login(staff)

    response = client.post(
        "/admin/catalog/groupdetails/add/",
        {
            "name": "unauthorized-team",
            "title": "",
            "description": "",
            "type": "team",
            "members": [],
        },
    )

    assert not GroupDetails.objects.filter(entity__name="unauthorized-team").exists()
    assert response.status_code == 403
