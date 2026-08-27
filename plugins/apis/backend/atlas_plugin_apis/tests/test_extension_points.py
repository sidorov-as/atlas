"""Tests for `resolve_endpoint`/`resolve_operation`."""

import pytest
from server.apps.catalog.tests.factories import create_api, create_system

from atlas_plugin_apis.extension_points import resolve_endpoint, resolve_operation
from atlas_plugin_apis.models import ApiEndpoint, ApiOperation

pytestmark = pytest.mark.django_db


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(name="billing-api", owner=group, system=system)


def test_resolve_endpoint_returns_the_row_with_its_api(api):
    endpoint = ApiEndpoint.objects.create(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )

    resolved = resolve_endpoint(endpoint.id)

    assert resolved is not None
    assert resolved.id == endpoint.id
    assert resolved.api_id == api.id


def test_resolve_endpoint_returns_none_for_a_nonexistent_id(api):
    assert resolve_endpoint("00000000-0000-0000-0000-000000000000") is None


def test_resolve_endpoint_returns_none_for_a_malformed_id():
    assert resolve_endpoint("not-a-uuid") is None


def test_resolve_operation_returns_the_row_with_its_api(api):
    operation = ApiOperation.objects.create(
        api=api,
        channel_address="orders.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="orders.created:send",
    )

    resolved = resolve_operation(operation.id)

    assert resolved is not None
    assert resolved.id == operation.id
    assert resolved.api_id == api.id


def test_resolve_operation_returns_none_for_a_nonexistent_id(api):
    assert resolve_operation("00000000-0000-0000-0000-000000000000") is None


def test_resolve_operation_returns_none_for_a_malformed_id():
    assert resolve_operation("not-a-uuid") is None
