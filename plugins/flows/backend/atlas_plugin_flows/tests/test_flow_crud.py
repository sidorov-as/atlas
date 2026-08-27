"""Flow CRUD API tests — split out of
`server.apps.catalog.tests.test_flow_crud`.

Covers the create/update happy path, the model-level validation rules
(missing system, unresolvable entity_ref, dangling transition targets,
transition cycles), that deleting a system with an attached Flow is
blocked at the ORM level (`on_delete=PROTECT`), and system/team filtering.
"""

import pytest
from atlas_plugin_api import get_catalog_entity_model
from django.db.models import ProtectedError
from server.apps.catalog.tests.factories import create_system

from atlas_plugin_flows.api.schemas import (
    _DESCRIPTION_MAX_LENGTH,
    _DOCUMENTATION_MAX_LENGTH,
    _STEPS_MAX_ITEMS,
)
from atlas_plugin_flows.models import Flow

pytestmark = pytest.mark.django_db


def _step(step_id, **kwargs):
    return {"id": step_id, "title": step_id, **kwargs}


def test_flow_created_with_valid_system_and_steps(owner_client, system, component):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "checkout-saga",
            "description": "Place order, charge, ship",
            "steps": [
                _step(
                    "place-order",
                    entity_ref="component:user-service",
                    title=None,
                    next_step={"id": "charge"},
                ),
                _step("charge"),
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "checkout-saga"
    assert body["system"] == "system:user-management"
    assert len(body["steps"]) == 2
    assert Flow.objects.filter(name="checkout-saga", system=system).exists()


def test_flow_update_happy_path(owner_client, system):
    flow = Flow.objects.create(
        system=system, name="original-flow", steps=[_step("start")]
    )

    response = owner_client.patch(
        f"/api/flows/{flow.id}/",
        {
            "description": "Updated description",
            "steps": [_step("start"), _step("end")],
        },
    )
    assert response.status_code == 200
    flow.refresh_from_db()
    assert flow.description == "Updated description"
    assert len(flow.steps) == 2


def test_flow_documentation_defaults_and_updates_independently(owner_client, system):
    flow = Flow.objects.create(
        system=system, name="documented-flow", steps=[_step("start")]
    )
    assert flow.documentation == ""

    response = owner_client.patch(
        f"/api/flows/{flow.id}/",
        {"documentation": "## Operations\n\nMonitor the queue."},
    )
    assert response.status_code == 200
    assert response.json()["documentation"] == "## Operations\n\nMonitor the queue."
    flow.refresh_from_db()
    assert flow.steps == [_step("start")]


def test_create_flow_with_oversized_description_is_rejected(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "oversized-description-flow",
            "description": "x" * (_DESCRIPTION_MAX_LENGTH + 1),
            "steps": [_step("start")],
        },
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="oversized-description-flow").exists()


def test_patch_flow_with_oversized_description_is_rejected(owner_client, system):
    flow = Flow.objects.create(
        system=system, name="patchable-flow", steps=[_step("start")]
    )
    response = owner_client.patch(
        f"/api/flows/{flow.id}/",
        {"description": "x" * (_DESCRIPTION_MAX_LENGTH + 1)},
    )
    assert response.status_code == 400
    flow.refresh_from_db()
    assert flow.description == ""


def test_create_flow_with_oversized_documentation_is_rejected(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "oversized-documentation-flow",
            "documentation": "x" * (_DOCUMENTATION_MAX_LENGTH + 1),
            "steps": [_step("start")],
        },
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="oversized-documentation-flow").exists()


def test_patch_flow_with_oversized_documentation_is_rejected(owner_client, system):
    flow = Flow.objects.create(
        system=system, name="patchable-flow-2", steps=[_step("start")]
    )
    response = owner_client.patch(
        f"/api/flows/{flow.id}/",
        {"documentation": "x" * (_DOCUMENTATION_MAX_LENGTH + 1)},
    )
    assert response.status_code == 400
    flow.refresh_from_db()
    assert flow.documentation == ""


def test_create_flow_with_too_many_steps_is_rejected(owner_client, system):
    too_many_steps = [_step(f"step-{i}") for i in range(_STEPS_MAX_ITEMS + 1)]
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "too-many-steps-flow",
            "steps": too_many_steps,
        },
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="too-many-steps-flow").exists()


def test_patch_flow_with_too_many_steps_is_rejected(owner_client, system):
    flow = Flow.objects.create(
        system=system, name="patchable-flow-3", steps=[_step("start")]
    )
    too_many_steps = [_step(f"step-{i}") for i in range(_STEPS_MAX_ITEMS + 1)]
    response = owner_client.patch(
        f"/api/flows/{flow.id}/",
        {"steps": too_many_steps},
    )
    assert response.status_code == 400
    flow.refresh_from_db()
    assert flow.steps == [_step("start")]


def test_flow_created_without_autolayout_fields_defaults(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "default-layout-flow",
            "steps": [_step("start")],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["autolayoutEnabled"] is True
    assert body["layoutDirection"] == "LAYOUT_LEFT_RIGHT"
    assert body["layoutEngine"] == "dagre"
    flow = Flow.objects.get(name="default-layout-flow")
    assert flow.autolayout_enabled is True
    assert flow.layout_direction == "LAYOUT_LEFT_RIGHT"
    assert flow.layout_engine == "dagre"


def test_flow_autolayout_fields_round_trip_through_create_and_update(
    owner_client, system
):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "manual-layout-flow",
            "steps": [_step("start")],
            "autolayout_enabled": False,
            "layout_direction": "LAYOUT_TOP_DOWN",
            "layout_engine": "elk",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["autolayoutEnabled"] is False
    assert body["layoutDirection"] == "LAYOUT_TOP_DOWN"
    assert body["layoutEngine"] == "elk"

    flow = Flow.objects.get(name="manual-layout-flow")
    response = owner_client.patch(
        f"/api/flows/{flow.id}/",
        {
            "autolayout_enabled": True,
            "layout_direction": "LAYOUT_LEFT_RIGHT",
            "layout_engine": "dagre",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["autolayoutEnabled"] is True
    assert body["layoutDirection"] == "LAYOUT_LEFT_RIGHT"
    assert body["layoutEngine"] == "dagre"
    flow.refresh_from_db()
    assert flow.autolayout_enabled is True
    assert flow.layout_direction == "LAYOUT_LEFT_RIGHT"
    assert flow.layout_engine == "dagre"


def test_flow_patch_changes_layout_engine_independently_of_other_fields(
    owner_client, system
):
    flow = Flow.objects.create(
        system=system,
        name="engine-only-patch-flow",
        steps=[_step("start")],
        layout_direction="LAYOUT_TOP_DOWN",
    )

    response = owner_client.patch(
        f"/api/flows/{flow.id}/",
        {"layout_engine": "elk"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["layoutEngine"] == "elk"
    assert body["layoutDirection"] == "LAYOUT_TOP_DOWN"
    flow.refresh_from_db()
    assert flow.layout_engine == "elk"
    assert flow.layout_direction == "LAYOUT_TOP_DOWN"


def test_flow_creation_without_system_is_rejected(owner_client):
    response = owner_client.post(
        "/api/flows/",
        {"name": "no-system-flow", "steps": []},
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="no-system-flow").exists()


@pytest.mark.parametrize("name", ["", "   ", "checkout/saga", "checkout:saga"])
def test_flow_creation_rejects_invalid_name(owner_client, name):
    response = owner_client.post(
        "/api/flows/",
        {"system": "system:user-management", "name": name, "steps": []},
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name=name).exists()


@pytest.mark.parametrize("name", ["", "   ", "checkout/saga", "checkout:saga"])
def test_flow_update_rejects_invalid_name(owner_client, system, name):
    flow = Flow.objects.create(
        system=system, name="original-flow", steps=[_step("start")]
    )

    response = owner_client.patch(
        f"/api/flows/{flow.id}/",
        {"name": name},
    )
    assert response.status_code == 400
    flow.refresh_from_db()
    assert flow.name == "original-flow"


def test_flow_update_omitting_name_leaves_it_unchanged(owner_client, system):
    flow = Flow.objects.create(
        system=system, name="original-flow", steps=[_step("start")]
    )

    response = owner_client.patch(
        f"/api/flows/{flow.id}/",
        {"description": "Updated description"},
    )
    assert response.status_code == 200
    flow.refresh_from_db()
    assert flow.name == "original-flow"


def test_flow_creation_rejects_unresolvable_entity_ref(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "broken-ref-flow",
            "steps": [_step("place-order", entity_ref="component:does-not-exist")],
        },
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="broken-ref-flow").exists()


def test_flow_creation_allows_reconverging_branches(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "reconverging-flow",
            "steps": [
                _step("start", next_steps=[{"id": "a"}, {"id": "b"}]),
                _step("a", next_step={"id": "end"}),
                _step("b", next_step={"id": "end"}),
                _step("end"),
            ],
        },
    )
    assert response.status_code == 201
    assert Flow.objects.filter(name="reconverging-flow").exists()


def test_flow_creation_rejects_self_transition(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "self-transition-flow",
            "steps": [_step("start", next_step={"id": "start"})],
        },
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="self-transition-flow").exists()


def test_flow_creation_rejects_multi_step_cycle(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "cyclic-flow",
            "steps": [
                _step("start", next_step={"id": "middle"}),
                _step("middle", next_step={"id": "start"}),
            ],
        },
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="cyclic-flow").exists()


def test_flow_creation_rejects_dangling_transition_target(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "dangling-target-flow",
            "steps": [_step("start", next_step={"id": "does-not-exist"})],
        },
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="dangling-target-flow").exists()


def test_flow_created_with_position_label_theme_and_external_label(
    owner_client, system
):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "canvas-flow",
            "steps": [
                _step("start", position={"x": 10, "y": 20.5}, label_theme="success"),
                _step("pay", external_label="Payment Gateway"),
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["steps"][0]["position"] == {"x": 10, "y": 20.5}
    assert body["steps"][0]["label_theme"] == "success"
    assert body["steps"][1]["external_label"] == "Payment Gateway"


def test_flow_creation_rejects_invalid_position_shape(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "bad-position-flow",
            "steps": [_step("start", position={"x": 10})],
        },
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="bad-position-flow").exists()


def test_flow_creation_rejects_invalid_label_theme(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "bad-label-theme-flow",
            "steps": [_step("start", label_theme="not-a-theme")],
        },
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="bad-label-theme-flow").exists()


def test_flow_creation_rejects_entity_ref_and_external_label_together(
    owner_client, system
):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "conflicting-ref-flow",
            "steps": [
                _step(
                    "start",
                    entity_ref="component:user-service",
                    external_label="Payment Gateway",
                )
            ],
        },
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="conflicting-ref-flow").exists()


def test_flow_creation_rejects_entity_ref_with_title(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "entity-ref-with-title-flow",
            "steps": [_step("place-order", entity_ref="component:user-service")],
        },
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="entity-ref-with-title-flow").exists()


def test_flow_creation_rejects_entity_ref_with_summary(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "entity-ref-with-summary-flow",
            "steps": [
                _step(
                    "place-order",
                    entity_ref="component:user-service",
                    title=None,
                    summary="Places the order",
                )
            ],
        },
    )
    assert response.status_code == 400
    assert not Flow.objects.filter(name="entity-ref-with-summary-flow").exists()


def test_flow_creation_saves_entity_ref_without_title_or_summary(
    owner_client, system, component
):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "entity-ref-only-flow",
            "steps": [
                _step("place-order", entity_ref="component:user-service", title=None)
            ],
        },
    )
    assert response.status_code == 201
    assert Flow.objects.filter(name="entity-ref-only-flow").exists()


def test_flow_creation_allows_title_and_summary_for_step_kind(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "step-kind-title-flow",
            "steps": [_step("start", summary="A plain step")],
        },
    )
    assert response.status_code == 201
    assert Flow.objects.filter(name="step-kind-title-flow").exists()


def test_flow_creation_allows_title_and_summary_for_external_kind(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "external-kind-title-flow",
            "steps": [
                _step(
                    "pay", external_label="Payment Gateway", summary="Charges the card"
                )
            ],
        },
    )
    assert response.status_code == 201
    assert Flow.objects.filter(name="external-kind-title-flow").exists()


def test_deleting_system_with_flow_is_blocked(system):
    Flow.objects.create(system=system, name="attached-flow", steps=[_step("start")])

    with pytest.raises(ProtectedError):
        system.delete()

    assert get_catalog_entity_model().objects.filter(pk=system.pk).exists()


def test_deleting_system_succeeds_after_flow_removed(system):
    flow = Flow.objects.create(
        system=system, name="removable-flow", steps=[_step("start")]
    )
    flow.delete()

    system.delete()
    assert not get_catalog_entity_model().objects.filter(pk=system.pk).exists()


def test_flow_list_filters_by_system(owner_client, system, group):
    other_system = create_system(name="billing", owner=group)
    Flow.objects.create(system=system, name="flow-in-user-management", steps=[])
    Flow.objects.create(system=other_system, name="flow-in-billing", steps=[])

    response = owner_client.get("/api/flows/", {"system": "system:user-management"})
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["page"]["objectList"]}
    assert names == {"flow-in-user-management"}


def test_flow_list_filters_by_team(owner_client, system, group, foreign_group):
    other_system = create_system(name="other-system", owner=foreign_group)
    Flow.objects.create(system=system, name="platform-flow", steps=[])
    Flow.objects.create(system=other_system, name="other-team-flow", steps=[])

    response = owner_client.get("/api/flows/", {"team": "group:platform"})
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["page"]["objectList"]}
    assert names == {"platform-flow"}


def test_flow_list_paginates_and_sorts_by_name(owner_client, system):
    Flow.objects.create(system=system, name="zebra-flow", steps=[])
    Flow.objects.create(system=system, name="alpha-flow", steps=[])

    response = owner_client.get("/api/flows/", {"page_size": 1, "sort": "name"})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["perPage"] == 1
    assert body["page"]["objectList"][0]["name"] == "alpha-flow"
