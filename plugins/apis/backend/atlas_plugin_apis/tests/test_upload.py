"""`(api, spec)` upload target (`apis-plugin` spec), exercising the adapter
directly: ticket issuance, scope/permission checks and the `PUT` route belong
to Core and are covered by its upload-ticket tests."""

import pytest
from atlas_plugin_api import UploadValidationError, get_upload_target
from server.apps.catalog.tests.factories import create_api, create_system

from atlas_plugin_apis.models import ApiDetails, ApiEndpoint, ApiOperation
from atlas_plugin_apis.tests.test_asyncapi_import import ASYNCAPI_2X_SPEC
from atlas_plugin_apis.tests.test_openapi_import import OPENAPI_3X_SPEC

pytestmark = pytest.mark.django_db


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def adapter():
    return get_upload_target("api", "spec").adapter


def _apply(adapter, api, body):
    return adapter.apply(api, body, adapter.validate_params({}), None)


def _details(api):
    return ApiDetails.objects.get(entity=api)


def _api(group, system, **kwargs):
    return create_api(name="billing", owner=group, system=system, **kwargs)


def test_target_requires_apis_write_and_the_spec_size_limit():
    target = get_upload_target("api", "spec")

    assert target.required_scope == "apis:write"
    assert target.max_bytes == 20 * 1024 * 1024


def test_valid_openapi_is_stored_and_endpoints_are_synchronized(adapter, group, system):
    api = _api(group, system)

    result = _apply(adapter, api, OPENAPI_3X_SPEC.encode())

    count = ApiEndpoint.objects.filter(api=api, status="active").count()
    assert count > 0
    assert result.summary == {"spec_kind": "openapi", "endpoints": count}
    assert _details(api).spec_content == OPENAPI_3X_SPEC


def test_valid_asyncapi_synchronizes_operations(adapter, group, system):
    api = _api(group, system, type="asyncapi")

    result = _apply(adapter, api, ASYNCAPI_2X_SPEC.encode())

    count = ApiOperation.objects.filter(api=api, status="active").count()
    assert count > 0
    assert result.summary == {"spec_kind": "asyncapi", "operations": count}


@pytest.mark.parametrize("body", [b"", b"   \n", b"a: [unclosed", b"\xff\xfe"])
def test_unusable_body_is_rejected_and_the_spec_is_unchanged(
    adapter, group, system, body
):
    api = _api(group, system)
    _apply(adapter, api, OPENAPI_3X_SPEC.encode())

    with pytest.raises(UploadValidationError):
        _apply(adapter, api, body)

    assert _details(api).spec_content == OPENAPI_3X_SPEC


def test_document_of_the_wrong_kind_is_rejected(adapter, group, system):
    api = _api(group, system)

    with pytest.raises(UploadValidationError, match="openapi"):
        _apply(adapter, api, ASYNCAPI_2X_SPEC.encode())

    assert _details(api).spec_content == ""


def test_document_over_parse_limits_is_rejected_and_the_spec_is_unchanged(
    adapter, group, system, monkeypatch
):
    api = _api(group, system)
    _apply(adapter, api, OPENAPI_3X_SPEC.encode())
    monkeypatch.setattr("atlas_plugin_apis.spec_fetch.MAX_SPEC_PARSE_NODES", 5)

    with pytest.raises(UploadValidationError, match="limits"):
        _apply(adapter, api, OPENAPI_3X_SPEC.encode() + b"\n")

    assert _details(api).spec_content == OPENAPI_3X_SPEC


def test_upload_switches_a_url_source_to_inline(adapter, group, system):
    api = _api(group, system)
    ApiDetails.objects.filter(entity=api).update(
        spec_source="url",
        spec_url="https://example.com/spec.yaml",
        spec_resolve_failed=True,
    )
    api = type(api).objects.get(pk=api.pk)

    _apply(adapter, api, OPENAPI_3X_SPEC.encode())

    details = _details(api)
    assert details.spec_source == "inline"
    assert details.spec_url == ""
    assert details.spec_resolve_failed is False
