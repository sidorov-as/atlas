"""`FlowService` contract tests (flows-plugin spec: "Flow CRUD is available
through a published FlowService contract").

Every Flow operation below goes exclusively through
`atlas_plugin_flows.extension_points.get_flow_service()` and the
`atlas_plugin_flows.contracts` DTOs/exception — never `atlas_plugin_flows.
api.views` helpers — to prove another plugin (namely the new `atlas.mcp`)
can list/get/create/update/delete a Flow through the published contract
alone, per the spec's "Another plugin performs Flow operations through
FlowService" scenario. `atlas_plugin_flows.models.Flow` is imported only to
assert on persisted state after the fact, not to perform any operation
itself.
"""

from http import HTTPStatus

import pytest
from dmr.response import APIError

from atlas_plugin_flows.contracts import FlowIn, FlowNotFoundError, FlowPatch
from atlas_plugin_flows.extension_points import get_flow_service
from atlas_plugin_flows.models import Flow

pytestmark = pytest.mark.django_db


def test_another_plugin_can_list_get_create_update_delete_via_flow_service(
    owner_user, system
):
    service = get_flow_service()
    actor = owner_user.actor_details.account

    created = service.create(
        body=FlowIn(system="system:user-management", name="contract-flow"),
        actor=actor,
    )
    assert Flow.objects.filter(pk=created.pk, name="contract-flow").exists()

    fetched = service.get(created.id)
    assert fetched.id == created.id

    listed = list(service.list(system="system:user-management"))
    assert created.id in {flow.id for flow in listed}

    updated = service.update(
        flow_id=created.id,
        body=FlowPatch(description="Updated via FlowService"),
        actor=actor,
    )
    assert updated.description == "Updated via FlowService"

    service.delete(flow_id=created.id, actor=actor)
    assert not Flow.objects.filter(pk=created.id).exists()


def test_flow_service_get_raises_not_found_for_missing_id():
    with pytest.raises(FlowNotFoundError):
        get_flow_service().get(999999)


def test_flow_service_applies_same_authorization_as_rest_controllers(
    non_member_account, system
):
    """FlowService applies the same authorization as the REST controllers
    (flows-plugin spec scenario): a non-member of the Flow's system's owner
    Group is rejected exactly as `atlas.flows.flow.edit` rejects it today.
    """
    service = get_flow_service()

    with pytest.raises(APIError) as exc_info:
        service.create(
            body=FlowIn(system="system:user-management", name="unauthorized-flow"),
            actor=non_member_account,
        )
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
    assert not Flow.objects.filter(name="unauthorized-flow").exists()
