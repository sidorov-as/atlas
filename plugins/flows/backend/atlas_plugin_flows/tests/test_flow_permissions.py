"""Flow write-permission tests (create/update/delete as non-member and as-member
behave the same as they did when Flow lived in Core).

Create/update/delete all require `atlas.flows.flow.edit`, checked against
the Flow's `system` — granted only to a member of that system's owner Group
(or a superuser); list/retrieve require only an authenticated session,
regardless of ownership.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from atlas_plugin_flows.models import Flow

pytestmark = pytest.mark.django_db


def _step(step_id, **kwargs):
    return {"id": step_id, "title": step_id, **kwargs}


def test_non_member_cannot_create_flow_under_foreign_system(non_member_client, system):
    response = non_member_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "unauthorized-flow",
            "steps": [],
        },
    )
    assert response.status_code == 403
    assert not Flow.objects.filter(name="unauthorized-flow").exists()


def test_non_member_cannot_update_flow_under_foreign_system(non_member_client, system):
    flow = Flow.objects.create(
        system=system, name="existing-flow", steps=[_step("start")]
    )

    response = non_member_client.patch(
        f"/api/flows/{flow.id}/",
        {"description": "Attempted update"},
    )
    assert response.status_code == 403
    flow.refresh_from_db()
    assert flow.description == ""


def test_non_member_cannot_delete_flow_under_foreign_system(non_member_client, system):
    flow = Flow.objects.create(
        system=system, name="existing-flow", steps=[_step("start")]
    )

    response = non_member_client.delete(f"/api/flows/{flow.id}/")
    assert response.status_code == 403
    assert Flow.objects.filter(pk=flow.pk).exists()


def test_member_can_create_update_and_delete_flow_under_their_system(
    owner_client, system
):
    create_response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "member-flow",
            "steps": [],
        },
    )
    assert create_response.status_code == 201
    flow = Flow.objects.get(name="member-flow")

    update_response = owner_client.patch(
        f"/api/flows/{flow.id}/",
        {"description": "Updated by member"},
    )
    assert update_response.status_code == 200

    delete_response = owner_client.delete(f"/api/flows/{flow.id}/")
    assert delete_response.status_code == 204
    assert not Flow.objects.filter(pk=flow.pk).exists()


def test_superuser_can_write_flow_under_any_system(dmr_client, system):
    superuser_account = get_user_model().objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password123",
    )
    dmr_client.force_login(superuser_account)

    response = dmr_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "superuser-flow",
            "steps": [],
        },
    )
    assert response.status_code == 201


def test_read_only_owner_cannot_mutate_flow(owner_client, owner_account, system):
    """A read-only owner cannot bypass Flow mutation through the API.

    The guarded evaluator denies `atlas.flows.flow.edit` before delegation,
    even for an owner who would otherwise be permitted.
    """
    flow = Flow.objects.create(
        system=system, name="existing-flow", steps=[_step("start")]
    )
    call_command(
        "clear_read_only",
        owner_account.username,
        reason="flow permission regression",
        read_only="true",
        confirm=True,
    )

    create_response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "read-only-flow",
            "steps": [],
        },
    )
    assert create_response.status_code == 403
    assert not Flow.objects.filter(name="read-only-flow").exists()

    update_response = owner_client.patch(
        f"/api/flows/{flow.id}/",
        {"description": "Attempted update"},
    )
    assert update_response.status_code == 403
    flow.refresh_from_db()
    assert flow.description == ""

    delete_response = owner_client.delete(f"/api/flows/{flow.id}/")
    assert delete_response.status_code == 403
    assert Flow.objects.filter(pk=flow.pk).exists()


def test_any_authenticated_user_can_read_flow_regardless_of_ownership(
    non_member_client, system
):
    Flow.objects.create(system=system, name="readable-flow", steps=[])

    list_response = non_member_client.get("/api/flows/")
    assert list_response.status_code == 200
    names = {item["name"] for item in list_response.json()["page"]["objectList"]}
    assert "readable-flow" in names

    flow = Flow.objects.get(name="readable-flow")
    detail_response = non_member_client.get(f"/api/flows/{flow.id}/")
    assert detail_response.status_code == 200


def test_detail_reports_edit_permission_to_a_member(owner_client, system):
    flow = Flow.objects.create(system=system, name="perm-flow", steps=[])

    body = owner_client.get(f"/api/flows/{flow.id}/").json()

    assert body["permissions"] == {"canEdit": True}


def test_detail_reports_no_edit_permission_to_a_non_member(non_member_client, system):
    flow = Flow.objects.create(system=system, name="perm-flow", steps=[])

    body = non_member_client.get(f"/api/flows/{flow.id}/").json()

    assert body["permissions"] == {"canEdit": False}
