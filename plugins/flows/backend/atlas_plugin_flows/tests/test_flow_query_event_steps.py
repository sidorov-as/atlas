"""Tests for `query_ref`/`event_ref` step validation."""

import pytest
from atlas_plugin_apis.models import ApiEndpoint, ApiOperation
from server.apps.catalog.tests.factories import create_api

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
def api(group, system):
    return create_api(name="orders-api", owner=group, system=system)


@pytest.fixture
def other_api(group, system):
    return create_api(name="payments-api", owner=group, system=system)


@pytest.fixture
def endpoint(api):
    return ApiEndpoint.objects.create(
        api=api, method=ApiEndpoint.METHOD_GET, path="/orders/{id}"
    )


@pytest.fixture
def operation(api):
    return ApiOperation.objects.create(
        api=api,
        channel_address="orders.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="orders.created:send",
    )


def _query_ref(api, endpoint, **overrides):
    return {
        "api": api.ref,
        "endpoint": str(endpoint.id),
        "method": endpoint.method,
        "path": endpoint.path,
        **overrides,
    }


def _event_ref(api, operation, **overrides):
    return {
        "api": api.ref,
        "operation": str(operation.id),
        "direction": operation.direction,
        "channel": operation.channel_address,
        **overrides,
    }


# --- model-level validate_steps() ------------------------------------------


def test_resolvable_query_ref_saves_successfully(api, endpoint):
    steps = [_step("fetch-order", query_ref=_query_ref(api, endpoint), title=None)]

    validate_steps(steps)


def test_resolvable_event_ref_saves_successfully(api, operation):
    steps = [_step("order-created", event_ref=_event_ref(api, operation), title=None)]

    validate_steps(steps)


def test_query_ref_with_title_is_rejected(api, endpoint):
    steps = [_step("fetch-order", query_ref=_query_ref(api, endpoint))]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_event_ref_with_summary_is_rejected(api, operation):
    steps = [
        _step(
            "order-created",
            event_ref=_event_ref(api, operation),
            title=None,
            summary="Emits the order",
        )
    ]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_query_ref_and_event_ref_are_mutually_exclusive(api, endpoint, operation):
    steps = [
        _step(
            "both",
            query_ref=_query_ref(api, endpoint),
            event_ref=_event_ref(api, operation),
        ),
    ]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_query_ref_and_entity_ref_are_mutually_exclusive(api, endpoint, component):
    steps = [
        _step(
            "both",
            entity_ref="component:user-service",
            query_ref=_query_ref(api, endpoint),
        ),
    ]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_entity_ref_with_title_is_rejected(component):
    steps = [_step("call-service", entity_ref="component:user-service")]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_entity_ref_with_summary_is_rejected(component):
    steps = [
        _step(
            "call-service",
            entity_ref="component:user-service",
            title=None,
            summary="Calls the service",
        ),
    ]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_entity_ref_alone_saves_successfully(component):
    steps = [_step("call-service", entity_ref="component:user-service", title=None)]

    validate_steps(steps)


def test_event_ref_and_external_label_are_mutually_exclusive(api, operation):
    steps = [
        _step(
            "both",
            external_label="Payment Gateway",
            event_ref=_event_ref(api, operation),
        ),
    ]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_query_ref_with_nonexistent_endpoint_is_rejected(api):
    steps = [
        _step(
            "fetch-order",
            query_ref=_query_ref(
                api, ApiEndpoint(id="00000000-0000-0000-0000-000000000000")
            ),
        ),
    ]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_query_ref_endpoint_belonging_to_a_different_api_is_rejected(
    api, other_api, endpoint
):
    steps = [_step("fetch-order", query_ref=_query_ref(other_api, endpoint))]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_event_ref_operation_belonging_to_a_different_api_is_rejected(
    api, other_api, operation
):
    steps = [_step("order-created", event_ref=_event_ref(other_api, operation))]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_query_ref_targeting_a_removed_endpoint_still_saves(api, endpoint):
    endpoint.status = ApiEndpoint.STATUS_REMOVED
    endpoint.save(update_fields=["status"])
    steps = [_step("fetch-order", query_ref=_query_ref(api, endpoint), title=None)]

    validate_steps(steps)


def test_event_ref_targeting_a_removed_operation_still_saves(api, operation):
    operation.status = ApiOperation.STATUS_REMOVED
    operation.save(update_fields=["status"])
    steps = [_step("order-created", event_ref=_event_ref(api, operation), title=None)]

    validate_steps(steps)


def test_query_ref_accepts_an_optional_summary(api, endpoint):
    steps = [
        _step(
            "fetch-order",
            query_ref=_query_ref(api, endpoint, summary="Fetch an order"),
            title=None,
        )
    ]

    validate_steps(steps)


def test_event_ref_accepts_an_optional_summary(api, operation):
    steps = [
        _step(
            "order-created",
            event_ref=_event_ref(api, operation, summary="Order was created"),
            title=None,
        )
    ]

    validate_steps(steps)


def test_query_ref_accepts_an_empty_summary(api, endpoint):
    steps = [
        _step(
            "fetch-order", query_ref=_query_ref(api, endpoint, summary=""), title=None
        )
    ]

    validate_steps(steps)


def test_query_ref_rejects_a_non_string_summary(api, endpoint):
    steps = [
        _step(
            "fetch-order", query_ref=_query_ref(api, endpoint, summary=123), title=None
        )
    ]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_query_ref_missing_required_key_is_rejected(api, endpoint):
    ref = _query_ref(api, endpoint)
    del ref["method"]
    steps = [_step("fetch-order", query_ref=ref)]

    with pytest.raises(StepValidationError):
        validate_steps(steps)


def test_query_ref_is_rejected_when_atlas_apis_is_not_installed(
    api, endpoint, monkeypatch
):
    monkeypatch.setattr(
        "atlas_plugin_flows.models.django_apps.is_installed", lambda name: False
    )
    steps = [_step("fetch-order", query_ref=_query_ref(api, endpoint), title=None)]

    with pytest.raises(StepValidationError, match="APIs plugin"):
        validate_steps(steps)


def test_event_ref_is_rejected_when_atlas_apis_is_not_installed(
    api, operation, monkeypatch
):
    monkeypatch.setattr(
        "atlas_plugin_flows.models.django_apps.is_installed", lambda name: False
    )
    steps = [_step("order-created", event_ref=_event_ref(api, operation), title=None)]

    with pytest.raises(StepValidationError, match="APIs plugin"):
        validate_steps(steps)


# --- HTTP API -----------------------------------------------------------


def test_flow_saved_with_query_ref_via_api(owner_client, system, api, endpoint):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "fetch-order-flow",
            "steps": [
                _step("fetch-order", query_ref=_query_ref(api, endpoint), title=None)
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["steps"][0]["query_ref"] == _query_ref(api, endpoint)
    assert Flow.objects.filter(name="fetch-order-flow").exists()


def test_flow_saved_with_event_ref_via_api(owner_client, system, api, operation):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "order-created-flow",
            "steps": [
                _step("order-created", event_ref=_event_ref(api, operation), title=None)
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["steps"][0]["event_ref"] == _event_ref(api, operation)
    assert Flow.objects.filter(name="order-created-flow").exists()


def test_flow_creation_rejects_unresolvable_query_ref(owner_client, system, api):
    response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "broken-query-ref-flow",
            "steps": [
                _step(
                    "fetch-order",
                    query_ref=_query_ref(
                        api, ApiEndpoint(id="00000000-0000-0000-0000-000000000000")
                    ),
                ),
            ],
        },
    )

    assert response.status_code == 400
    assert not Flow.objects.filter(name="broken-query-ref-flow").exists()


# --- read-time ref status -----------------


def test_resolve_step_ref_statuses_reports_a_removed_endpoint(api, endpoint):
    endpoint.status = ApiEndpoint.STATUS_REMOVED
    endpoint.save(update_fields=["status"])
    steps = [_step("fetch-order", query_ref=_query_ref(api, endpoint))]

    assert resolve_step_ref_statuses(steps) == {
        "fetch-order": {"status": "removed", "deprecated": False}
    }


def test_resolve_step_ref_statuses_reports_a_deprecated_endpoint(api, endpoint):
    endpoint.deprecated = True
    endpoint.save(update_fields=["deprecated"])
    steps = [_step("fetch-order", query_ref=_query_ref(api, endpoint))]

    assert resolve_step_ref_statuses(steps) == {
        "fetch-order": {"status": "active", "deprecated": True}
    }


def test_resolve_step_ref_statuses_reports_a_removed_operation(api, operation):
    operation.status = ApiOperation.STATUS_REMOVED
    operation.save(update_fields=["status"])
    steps = [_step("order-created", event_ref=_event_ref(api, operation))]

    assert resolve_step_ref_statuses(steps) == {
        "order-created": {"status": "removed", "deprecated": False}
    }


def test_resolve_step_ref_statuses_reports_event_ref_direction_channel_drift(
    api, operation
):
    steps = [
        _step(
            "order-created",
            event_ref=_event_ref(
                api,
                operation,
                direction=ApiOperation.DIRECTION_RECEIVE,
                channel="orders.legacy",
            ),
        ),
    ]

    assert resolve_step_ref_statuses(steps) == {
        "order-created": {
            "status": "active",
            "deprecated": False,
            "live": {
                "direction": operation.direction,
                "channel_address": operation.channel_address,
            },
        },
    }


def test_resolve_step_ref_statuses_reports_no_drift_when_event_ref_matches(
    api, operation
):
    steps = [_step("order-created", event_ref=_event_ref(api, operation))]

    assert resolve_step_ref_statuses(steps) == {
        "order-created": {"status": "active", "deprecated": False}
    }


def test_resolve_step_ref_statuses_reports_event_ref_summary_drift_independent_of_direction_channel(
    api, operation
):
    operation.summary = "New summary from a re-import"
    operation.save(update_fields=["summary"])
    steps = [
        _step(
            "order-created", event_ref=_event_ref(api, operation, summary="Old summary")
        )
    ]

    assert resolve_step_ref_statuses(steps) == {
        "order-created": {
            "status": "active",
            "deprecated": False,
            "live": {"summary": "New summary from a re-import"},
        },
    }


def test_resolve_step_ref_statuses_reports_event_ref_summary_and_direction_channel_drift_together(
    api, operation
):
    operation.summary = "New summary from a re-import"
    operation.save(update_fields=["summary"])
    steps = [
        _step(
            "order-created",
            event_ref=_event_ref(
                api,
                operation,
                direction=ApiOperation.DIRECTION_RECEIVE,
                channel="orders.legacy",
                summary="Old summary",
            ),
        ),
    ]

    assert resolve_step_ref_statuses(steps) == {
        "order-created": {
            "status": "active",
            "deprecated": False,
            "live": {
                "direction": operation.direction,
                "channel_address": operation.channel_address,
                "summary": "New summary from a re-import",
            },
        },
    }


def test_resolve_step_ref_statuses_reports_query_ref_summary_drift(api, endpoint):
    endpoint.summary = "New summary from a re-import"
    endpoint.save(update_fields=["summary"])
    steps = [
        _step("fetch-order", query_ref=_query_ref(api, endpoint, summary="Old summary"))
    ]

    assert resolve_step_ref_statuses(steps) == {
        "fetch-order": {
            "status": "active",
            "deprecated": False,
            "live": {"summary": "New summary from a re-import"},
        },
    }


def test_resolve_step_ref_statuses_reports_no_drift_when_query_ref_summary_matches(
    api, endpoint
):
    endpoint.summary = "Fetch an order"
    endpoint.save(update_fields=["summary"])
    steps = [
        _step(
            "fetch-order", query_ref=_query_ref(api, endpoint, summary="Fetch an order")
        )
    ]

    assert resolve_step_ref_statuses(steps) == {
        "fetch-order": {"status": "active", "deprecated": False}
    }


def test_resolve_step_ref_statuses_reports_no_query_ref_drift_when_summary_is_unset_and_endpoint_summary_is_blank(
    api, endpoint
):
    steps = [_step("fetch-order", query_ref=_query_ref(api, endpoint))]

    assert resolve_step_ref_statuses(steps) == {
        "fetch-order": {"status": "active", "deprecated": False}
    }


def test_resolve_step_ref_statuses_omits_an_event_ref_that_no_longer_resolves(api):
    steps = [
        _step(
            "order-created",
            event_ref=_event_ref(
                api, ApiOperation(id="00000000-0000-0000-0000-000000000000")
            ),
        ),
    ]

    assert resolve_step_ref_statuses(steps) == {}


def test_resolve_step_ref_statuses_is_empty_for_event_ref_when_atlas_apis_is_not_installed(
    api, operation, monkeypatch
):
    monkeypatch.setattr(
        "atlas_plugin_flows.models.django_apps.is_installed", lambda name: False
    )
    steps = [_step("order-created", event_ref=_event_ref(api, operation))]

    assert resolve_step_ref_statuses(steps) == {}


def test_resolve_step_ref_statuses_reports_an_active_non_deprecated_endpoint(
    api, endpoint
):
    steps = [_step("fetch-order", query_ref=_query_ref(api, endpoint))]

    assert resolve_step_ref_statuses(steps) == {
        "fetch-order": {"status": "active", "deprecated": False}
    }


def test_resolve_step_ref_statuses_omits_a_reference_that_no_longer_resolves(api):
    steps = [
        _step(
            "fetch-order",
            query_ref=_query_ref(
                api, ApiEndpoint(id="00000000-0000-0000-0000-000000000000")
            ),
        ),
    ]

    assert resolve_step_ref_statuses(steps) == {}


def test_resolve_step_ref_statuses_reports_an_active_entity_ref(api, component):
    steps = [_step("call-service", entity_ref="component:user-service")]

    assert resolve_step_ref_statuses(steps) == {
        "call-service": {
            "status": "active",
            "deprecated": False,
            "title": "",
            "description": "",
        },
    }


def test_resolve_step_ref_statuses_reports_entity_ref_title_and_description(
    api, component
):
    component.title = "User Service"
    component.description = "Owns user accounts"
    component.save(update_fields=["title", "description"])
    steps = [_step("call-service", entity_ref="component:user-service")]

    assert resolve_step_ref_statuses(steps) == {
        "call-service": {
            "status": "active",
            "deprecated": False,
            "title": "User Service",
            "description": "Owns user accounts",
        },
    }


def test_resolve_step_ref_statuses_reports_live_data_uniformly_for_actor_and_team(
    api, owner_user, group
):
    steps = [
        _step("notify-owner", entity_ref=owner_user.ref),
        _step("assign-team", entity_ref=group.ref),
    ]

    result = resolve_step_ref_statuses(steps)

    assert result["notify-owner"] == {
        "status": "active",
        "deprecated": False,
        "title": owner_user.title,
        "description": owner_user.description,
    }
    assert result["assign-team"] == {
        "status": "active",
        "deprecated": False,
        "title": group.title,
        "description": group.description,
    }


def test_resolve_step_ref_statuses_is_empty_without_a_ref(api):
    steps = [_step("no-op")]

    assert resolve_step_ref_statuses(steps) == {}


def test_resolve_step_ref_statuses_reports_a_removed_entity_ref(api, component):
    component.status = "removed"
    component.save(update_fields=["status"])
    steps = [_step("call-service", entity_ref="component:user-service")]

    assert resolve_step_ref_statuses(steps) == {
        "call-service": {
            "status": "removed",
            "deprecated": False,
            "title": "",
            "description": "",
        },
    }


def test_resolve_step_ref_statuses_reports_a_deprecated_entity_ref(api, component):
    component.component_details.lifecycle = "deprecated"
    component.component_details.save(update_fields=["lifecycle"])
    steps = [_step("call-service", entity_ref="component:user-service")]

    assert resolve_step_ref_statuses(steps) == {
        "call-service": {
            "status": "active",
            "deprecated": True,
            "title": "",
            "description": "",
        },
    }


def test_resolve_step_ref_statuses_omits_an_entity_ref_that_no_longer_resolves(api):
    steps = [_step("call-service", entity_ref="component:does-not-exist")]

    assert resolve_step_ref_statuses(steps) == {}


def test_resolve_step_ref_statuses_is_empty_when_atlas_apis_is_not_installed(
    api, endpoint, monkeypatch
):
    monkeypatch.setattr(
        "atlas_plugin_flows.models.django_apps.is_installed", lambda name: False
    )
    steps = [_step("fetch-order", query_ref=_query_ref(api, endpoint))]

    assert resolve_step_ref_statuses(steps) == {}


def test_flow_read_via_api_surfaces_ref_status(
    owner_client, system, api, endpoint, operation
):
    endpoint.deprecated = True
    endpoint.save(update_fields=["deprecated"])
    operation.status = ApiOperation.STATUS_REMOVED
    operation.save(update_fields=["status"])

    create_response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "status-flow",
            "steps": [
                _step("fetch-order", query_ref=_query_ref(api, endpoint), title=None),
                _step(
                    "order-created", event_ref=_event_ref(api, operation), title=None
                ),
            ],
        },
    )
    assert create_response.status_code == 201
    flow_id = create_response.json()["id"]

    response = owner_client.get(f"/api/flows/{flow_id}/")

    assert response.status_code == 200
    body = response.json()
    assert body["refStatus"]["fetch-order"] == {"status": "active", "deprecated": True}
    assert body["refStatus"]["order-created"] == {
        "status": "removed",
        "deprecated": False,
    }
    # The stored snapshot itself is never touched by read-time resolution.
    assert body["steps"][0]["query_ref"] == _query_ref(api, endpoint)


def test_flow_read_via_api_surfaces_removed_entity_ref_status(
    owner_client, system, component
):
    component.status = "removed"
    component.save(update_fields=["status"])

    create_response = owner_client.post(
        "/api/flows/",
        {
            "system": "system:user-management",
            "name": "entity-ref-flow",
            "steps": [
                _step("call-service", entity_ref="component:user-service", title=None)
            ],
        },
    )
    assert create_response.status_code == 201
    flow_id = create_response.json()["id"]

    response = owner_client.get(f"/api/flows/{flow_id}/")

    assert response.status_code == 200
    body = response.json()
    assert body["refStatus"]["call-service"] == {
        "status": "removed",
        "deprecated": False,
        "title": "",
        "description": "",
    }
    # The stored ref is never touched by read-time resolution.
    assert body["steps"][0]["entity_ref"] == "component:user-service"
