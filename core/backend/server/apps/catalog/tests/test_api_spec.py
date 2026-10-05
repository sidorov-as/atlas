"""API spec-source CRUD tests."""

from unittest.mock import patch

import pytest
from atlas_plugin_api import SafeHttpError, SafeHttpResponse
from atlas_plugin_apis import spec_fetch
from atlas_plugin_apis.api.schemas import _SPEC_CONTENT_MAX_LENGTH
from atlas_plugin_apis.models import ApiDetails, ApiEndpoint, ApiOperation

from server.apps.catalog.models import KIND_API, CatalogEntity

pytestmark = pytest.mark.django_db

SPEC_FETCH_PATCH_TARGET = "atlas_plugin_apis.spec_fetch.safe_request"


def _fake_success(
    text: str, *, url: str = "https://example.com/spec.yaml"
) -> SafeHttpResponse:
    """A `safe_request` return value shaped like a successful fetch — the
    fields `fetch_spec_content` doesn't inspect (`headers`,
    `resolved_address`) are filler."""
    return SafeHttpResponse(
        status_code=200,
        headers={},
        url=url,
        resolved_address="203.0.113.1",
        content=text.encode(),
    )


INLINE_OPENAPI_SPEC = """
openapi: "3.0.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      summary: List invoices
      responses:
        '200': {description: OK}
"""

INLINE_ASYNCAPI_SPEC = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
channels:
  booking.confirmed:
    publish:
      operationId: onBookingConfirmed
      summary: Receive booking-confirmation events
"""


def test_create_api_with_none_spec_source_leaves_content_empty(
    owner_client, group, system
):
    response = owner_client.post(
        "/api/apis/",
        {
            "metadata": {"name": "no-spec-api"},
            "spec": {
                "type": "grpc",
                "owner": "group:platform",
                "system": "system:user-management",
            },
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["spec"]["specSource"] == "none"
    assert body["spec"]["specContent"] == ""
    assert body["spec"]["specResolveFailed"] is False


def test_create_api_with_inline_spec_source(owner_client, group, system):
    response = owner_client.post(
        "/api/apis/",
        {
            "metadata": {"name": "inline-api"},
            "spec": {
                "type": "openapi",
                "owner": "group:platform",
                "system": "system:user-management",
                "specSource": "inline",
                "specContent": "openapi: 3.0.0",
            },
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["spec"]["specSource"] == "inline"
    assert body["spec"]["specContent"] == "openapi: 3.0.0"


def test_create_api_with_url_spec_source_resolves_synchronously(
    owner_client, group, system
):
    with patch(SPEC_FETCH_PATCH_TARGET) as mock_get:
        mock_get.return_value = _fake_success("openapi: 3.0.0")
        response = owner_client.post(
            "/api/apis/",
            {
                "metadata": {"name": "url-api"},
                "spec": {
                    "type": "openapi",
                    "owner": "group:platform",
                    "system": "system:user-management",
                    "specSource": "url",
                    "specUrl": "https://example.com/openapi.yaml",
                },
            },
        )

    assert response.status_code == 201
    mock_get.assert_called_once_with(
        "https://example.com/openapi.yaml",
        timeout=spec_fetch.REQUEST_TIMEOUT_SECONDS,
        max_response_bytes=spec_fetch.MAX_SPEC_RESPONSE_BYTES,
        allow_http=False,
        exempt_hosts=(),
    )
    body = response.json()
    assert body["spec"]["specSource"] == "url"
    assert body["spec"]["specContent"] == "openapi: 3.0.0"
    assert body["spec"]["specResolvedAt"] is not None
    assert body["spec"]["specResolveFailed"] is False


def test_create_api_with_url_spec_source_flags_failed_fetch(
    owner_client, group, system
):
    with patch(SPEC_FETCH_PATCH_TARGET) as mock_get:
        mock_get.side_effect = SafeHttpError("boom")
        response = owner_client.post(
            "/api/apis/",
            {
                "metadata": {"name": "broken-url-api"},
                "spec": {
                    "type": "openapi",
                    "owner": "group:platform",
                    "system": "system:user-management",
                    "specSource": "url",
                    "specUrl": "https://example.com/openapi.yaml",
                },
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["spec"]["specContent"] == ""
    assert body["spec"]["specResolveFailed"] is True


def test_create_api_with_oversized_inline_spec_content_is_rejected(
    owner_client, group, system
):
    response = owner_client.post(
        "/api/apis/",
        {
            "metadata": {"name": "oversized-inline-api"},
            "spec": {
                "type": "openapi",
                "owner": "group:platform",
                "system": "system:user-management",
                "specSource": "inline",
                "specContent": "x" * (_SPEC_CONTENT_MAX_LENGTH + 1),
            },
        },
    )
    assert response.status_code == 400
    assert not CatalogEntity.objects.filter(
        kind=KIND_API, name="oversized-inline-api"
    ).exists()


def test_patch_with_oversized_inline_spec_content_is_rejected(
    owner_client, api
):
    response = owner_client.patch(
        f"/api/apis/{api.id}/",
        {
            "spec": {
                "specSource": "inline",
                "specContent": "x" * (_SPEC_CONTENT_MAX_LENGTH + 1),
            }
        },
    )
    assert response.status_code == 400
    details = api.api_details
    details.refresh_from_db()
    assert details.spec_source == "none"
    assert details.spec_content == ""


def test_create_api_with_large_url_spec_unaffected_by_inline_limit(
    owner_client, group, system
):
    """The inline `spec_content` size limit is enforced at the Pydantic
    request-body layer; `url`-sourced content is written directly onto the
    model after fetch (`spec_fetch.resolve_api_spec_url`), bypassing that
    limit entirely — bounded instead by `spec_fetch.MAX_SPEC_RESPONSE_BYTES`.
    """
    large_content = "x" * (_SPEC_CONTENT_MAX_LENGTH + 1)
    with patch(SPEC_FETCH_PATCH_TARGET) as mock_get:
        mock_get.return_value = _fake_success(large_content)
        response = owner_client.post(
            "/api/apis/",
            {
                "metadata": {"name": "large-url-api"},
                "spec": {
                    "type": "openapi",
                    "owner": "group:platform",
                    "system": "system:user-management",
                    "specSource": "url",
                    "specUrl": "https://example.com/openapi.yaml",
                },
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["spec"]["specContent"] == large_content


def test_updating_spec_source_to_none_clears_fields(owner_client, api):
    details = api.api_details
    details.spec_source = "inline"
    details.spec_content = "openapi: 3.0.0"
    details.save(update_fields=["spec_source", "spec_content"])

    response = owner_client.patch(
        f"/api/apis/{api.id}/", {"spec": {"specSource": "none"}}
    )

    assert response.status_code == 200
    details.refresh_from_db()
    assert details.spec_source == "none"
    assert details.spec_content == ""
    assert details.spec_url == ""
    assert details.spec_resolved_at is None
    assert details.spec_resolve_failed is False


def test_updating_spec_source_to_url_resolves_synchronously(owner_client, api):
    with patch(SPEC_FETCH_PATCH_TARGET) as mock_get:
        mock_get.return_value = _fake_success("asyncapi: 3.0.0")
        response = owner_client.patch(
            f"/api/apis/{api.id}/",
            {
                "spec": {
                    "specSource": "url",
                    "specUrl": "https://example.com/asyncapi.yaml",
                }
            },
        )

    assert response.status_code == 200
    details = api.api_details
    details.refresh_from_db()
    assert details.spec_source == "url"
    assert details.spec_url == "https://example.com/asyncapi.yaml"
    assert details.spec_content == "asyncapi: 3.0.0"
    assert details.spec_resolve_failed is False


# --- Endpoint sync on the create/patch write paths — the periodic-refresh
# write path is covered by
# `atlas_plugin_ingestion.tests.test_spec_refresh` instead. -----------------


def test_create_api_with_inline_openapi_spec_produces_endpoints_synchronously(
    owner_client, group, system
):
    response = owner_client.post(
        "/api/apis/",
        {
            "metadata": {"name": "synced-api"},
            "spec": {
                "type": "openapi",
                "owner": "group:platform",
                "system": "system:user-management",
                "specSource": "inline",
                "specContent": INLINE_OPENAPI_SPEC,
            },
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["spec"]["endpointsSyncFailed"] is False
    assert body["spec"]["endpointsSyncedAt"] is not None
    endpoint = ApiEndpoint.objects.get(
        api_id=body["id"], method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )
    assert endpoint.operation_id == "listInvoices"


def test_patch_updating_spec_content_resyncs_endpoints(owner_client, api):
    response = owner_client.patch(
        f"/api/apis/{api.id}/",
        {"spec": {"specSource": "inline", "specContent": INLINE_OPENAPI_SPEC}},
    )

    assert response.status_code == 200
    assert ApiEndpoint.objects.filter(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    ).exists()


def test_create_non_openapi_typed_api_never_syncs_endpoints(
    owner_client, group, system
):
    response = owner_client.post(
        "/api/apis/",
        {
            "metadata": {"name": "grpc-api"},
            "spec": {
                "type": "grpc",
                "owner": "group:platform",
                "system": "system:user-management",
                "specSource": "inline",
                "specContent": "service Foo {}",
            },
        },
    )

    assert response.status_code == 201
    assert not ApiEndpoint.objects.filter(api_id=response.json()["id"]).exists()


def test_create_api_with_empty_spec_content_never_syncs_endpoints(
    owner_client, group, system
):
    response = owner_client.post(
        "/api/apis/",
        {
            "metadata": {"name": "no-spec-api"},
            "spec": {
                "type": "openapi",
                "owner": "group:platform",
                "system": "system:user-management",
            },
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["spec"]["endpointsSyncedAt"] is None
    assert not ApiEndpoint.objects.filter(api_id=body["id"]).exists()


# --- Operation sync on the create/patch write paths — the periodic-refresh
# write path is covered by
# `atlas_plugin_ingestion.tests.test_spec_refresh` instead. ------------------


def test_create_api_with_inline_asyncapi_spec_produces_operations_synchronously(
    owner_client, group, system
):
    response = owner_client.post(
        "/api/apis/",
        {
            "metadata": {"name": "synced-asyncapi-api"},
            "spec": {
                "type": "asyncapi",
                "owner": "group:platform",
                "system": "system:user-management",
                "specSource": "inline",
                "specContent": INLINE_ASYNCAPI_SPEC,
            },
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["spec"]["operationsSyncFailed"] is False
    assert body["spec"]["operationsSyncedAt"] is not None
    operation = ApiOperation.objects.get(
        api_id=body["id"], operation_key="booking.confirmed-receive"
    )
    assert operation.operation_id == "onBookingConfirmed"


def test_patch_updating_spec_content_resyncs_operations(
    owner_client, group, system
):
    entity = CatalogEntity.objects.create(
        kind=KIND_API, name="patchable-asyncapi-api", owner=group
    )
    api = ApiDetails.objects.create(
        entity=entity, type=ApiDetails.TYPE_ASYNCAPI, system=system
    ).entity

    response = owner_client.patch(
        f"/api/apis/{api.id}/",
        {"spec": {"specSource": "inline", "specContent": INLINE_ASYNCAPI_SPEC}},
    )

    assert response.status_code == 200
    assert ApiOperation.objects.filter(
        api=api, operation_key="booking.confirmed-receive"
    ).exists()


def test_create_non_asyncapi_typed_api_never_syncs_operations(
    owner_client, group, system
):
    response = owner_client.post(
        "/api/apis/",
        {
            "metadata": {"name": "grpc-api-2"},
            "spec": {
                "type": "grpc",
                "owner": "group:platform",
                "system": "system:user-management",
                "specSource": "inline",
                "specContent": "service Foo {}",
            },
        },
    )

    assert response.status_code == 201
    assert not ApiOperation.objects.filter(
        api_id=response.json()["id"]
    ).exists()


def test_create_api_with_empty_spec_content_never_syncs_operations(
    owner_client, group, system
):
    response = owner_client.post(
        "/api/apis/",
        {
            "metadata": {"name": "no-spec-asyncapi-api"},
            "spec": {
                "type": "asyncapi",
                "owner": "group:platform",
                "system": "system:user-management",
            },
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["spec"]["operationsSyncedAt"] is None
    assert not ApiOperation.objects.filter(api_id=body["id"]).exists()
