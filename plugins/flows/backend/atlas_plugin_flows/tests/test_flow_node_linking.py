"""Tests for `flow_ref`/`link_url` step validation and live status."""

import pytest

from atlas_plugin_flows.models import (
    Flow,
    StepValidationError,
    resolve_step_ref_statuses,
    validate_steps,
)

pytestmark = pytest.mark.django_db


def _step(step_id, **kwargs):
    return {"id": step_id, "title": step_id, **kwargs}


@pytest.fixture
def target_flow(system):
    return Flow.objects.create(
        system=system, name="checkout", description="Cart to payment"
    )


# --- flow_ref ---------------------------------------------------------------


def test_resolvable_flow_ref_saves_successfully(target_flow):
    steps = [_step("continue-elsewhere", flow_ref=target_flow.id, title=None)]

    validate_steps(steps)


def test_flow_ref_with_title_is_rejected(target_flow):
    steps = [_step("continue-elsewhere", flow_ref=target_flow.id)]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_flow_ref_with_summary_is_rejected(target_flow):
    steps = [
        _step(
            "continue-elsewhere",
            flow_ref=target_flow.id,
            title=None,
            summary="Goes to checkout",
        )
    ]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_flow_ref_and_entity_ref_are_mutually_exclusive(target_flow, component):
    steps = [
        _step("both", entity_ref="component:user-service", flow_ref=target_flow.id)
    ]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_flow_ref_and_external_label_are_mutually_exclusive(target_flow):
    steps = [_step("both", external_label="Payment Gateway", flow_ref=target_flow.id)]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_flow_ref_with_nonexistent_flow_is_rejected():
    steps = [_step("continue-elsewhere", flow_ref=999999, title=None)]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_flow_ref_with_non_integer_value_is_rejected():
    steps = [_step("continue-elsewhere", flow_ref="not-an-int", title=None)]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_flow_node_may_reference_its_own_flow(system):
    flow = Flow.objects.create(system=system, name="self-linking", steps=[])
    steps = [_step("link-back", flow_ref=flow.id, title=None)]

    validate_steps(steps)


# --- link_url -----------------------------------------------------------


def test_link_url_saves_successfully():
    steps = [_step("see-runbook", link_url="https://example.com/runbook", title=None)]

    validate_steps(steps)


def test_link_url_may_carry_its_own_title_and_summary():
    steps = [
        _step(
            "see-runbook",
            link_url="https://example.com/runbook",
            title="Incident runbook",
            summary="What to do when checkout is down",
        ),
    ]

    validate_steps(steps)


def test_link_url_with_disallowed_scheme_is_rejected():
    steps = [_step("see-runbook", link_url="javascript:alert(1)", title=None)]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_link_url_that_is_not_well_formed_is_rejected():
    steps = [_step("see-runbook", link_url="not a url", title=None)]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_link_url_and_flow_ref_are_mutually_exclusive(target_flow):
    steps = [
        _step(
            "both", link_url="https://example.com", flow_ref=target_flow.id, title=None
        )
    ]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_link_url_and_entity_ref_are_mutually_exclusive(component):
    steps = [
        _step(
            "both", entity_ref="component:user-service", link_url="https://example.com"
        )
    ]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


# --- HTTP API -----------------------------------------------------------


def test_flow_saved_with_flow_ref_via_api(owner_client, system, target_flow):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "continue-elsewhere-flow",
            "steps": [_step("continue-elsewhere", flow_ref=target_flow.id, title=None)],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["steps"][0]["flow_ref"] == target_flow.id
    assert Flow.objects.filter(name="continue-elsewhere-flow").exists()


def test_flow_creation_rejects_unresolvable_flow_ref(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "broken-flow-ref-flow",
            "steps": [_step("continue-elsewhere", flow_ref=999999, title=None)],
        },
    )

    assert response.status_code == 400
    assert not Flow.objects.filter(name="broken-flow-ref-flow").exists()


def test_flow_saved_with_link_url_via_api(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "see-runbook-flow",
            "steps": [
                _step("see-runbook", link_url="https://example.com/runbook", title=None)
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["steps"][0]["link_url"] == "https://example.com/runbook"
    assert Flow.objects.filter(name="see-runbook-flow").exists()


def test_flow_creation_rejects_disallowed_link_url_scheme(owner_client, system):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "bad-link-flow",
            "steps": [_step("see-runbook", link_url="javascript:alert(1)", title=None)],
        },
    )

    assert response.status_code == 400
    assert not Flow.objects.filter(name="bad-link-flow").exists()


# --- read-time ref status -----------------


def test_resolve_step_ref_statuses_reports_flow_ref_name_and_description(target_flow):
    steps = [_step("continue-elsewhere", flow_ref=target_flow.id, title=None)]

    assert resolve_step_ref_statuses(steps) == {
        "continue-elsewhere": {"name": "checkout", "description": "Cart to payment"},
    }


def test_resolve_step_ref_statuses_omits_a_flow_ref_that_no_longer_resolves():
    steps = [_step("continue-elsewhere", flow_ref=999999, title=None)]

    assert resolve_step_ref_statuses(steps) == {}


def test_resolve_step_ref_statuses_is_empty_without_a_flow_ref():
    steps = [_step("no-op")]

    assert resolve_step_ref_statuses(steps) == {}


def test_resolve_step_ref_statuses_reports_flow_ref_uniformly_regardless_of_atlas_apis(
    target_flow, monkeypatch
):
    monkeypatch.setattr(
        "atlas_plugin_flows.models.django_apps.is_installed", lambda name: False
    )
    steps = [_step("continue-elsewhere", flow_ref=target_flow.id, title=None)]

    assert resolve_step_ref_statuses(steps) == {
        "continue-elsewhere": {"name": "checkout", "description": "Cart to payment"},
    }


def test_flow_read_via_api_surfaces_flow_ref_status(owner_client, system, target_flow):
    create_response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "continue-elsewhere-flow",
            "steps": [_step("continue-elsewhere", flow_ref=target_flow.id, title=None)],
        },
    )
    assert create_response.status_code == 201
    flow_id = create_response.json()["id"]

    response = owner_client.get(f"/api/flows/{flow_id}/")

    assert response.status_code == 200
    body = response.json()
    assert body["refStatus"]["continue-elsewhere"] == {
        "name": "checkout",
        "description": "Cart to payment",
    }
    # The stored reference itself is never touched by read-time resolution.
    assert body["steps"][0]["flow_ref"] == target_flow.id


def test_flow_read_via_api_succeeds_when_flow_ref_target_is_deleted(
    owner_client, system, target_flow
):
    create_response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "dangling-flow-ref-flow",
            "steps": [_step("continue-elsewhere", flow_ref=target_flow.id, title=None)],
        },
    )
    assert create_response.status_code == 201
    flow_id = create_response.json()["id"]
    deleted_flow_id = target_flow.id
    target_flow.delete()

    response = owner_client.get(f"/api/flows/{flow_id}/")

    assert response.status_code == 200
    body = response.json()
    assert "continue-elsewhere" not in body["refStatus"]
    assert body["steps"][0]["flow_ref"] == deleted_flow_id
