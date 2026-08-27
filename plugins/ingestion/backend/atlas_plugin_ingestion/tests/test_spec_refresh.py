"""`refresh_spec_urls` tests.

Endpoint sync on this same write path is tested against `atlas_plugin_apis.extension_points.due_for_spec_
refresh` directly in that plugin's own test suite instead of here —
`atlas_plugin_apis.models.ApiEndpoint` is a Django model, not a declared
contract type, so this plugin's tests (like its own code) may not import it
(`server.apps.plugins.tests.test_import_boundaries`)."""

from unittest.mock import patch

import pytest
from atlas_plugin_api import SafeHttpError, SafeHttpResponse
from atlas_plugin_apis.contracts import SPEC_SOURCE_INLINE, SPEC_SOURCE_URL
from server.apps.catalog.tests.factories import create_api

from atlas_plugin_ingestion.pipeline import refresh_spec_urls

pytestmark = pytest.mark.django_db

SPEC_FETCH_PATCH_TARGET = "atlas_plugin_apis.spec_fetch.safe_request"
STALE_CONTENT = "openapi: 3.0.0  # last-good"


def _fake_success(text: str, *, url: str = "https://example.com/spec.yaml") -> SafeHttpResponse:
    return SafeHttpResponse(
        status_code=200,
        headers={},
        url=url,
        resolved_address="203.0.113.1",
        content=text.encode(),
    )


@pytest.fixture
def url_api(group, system):
    entity = create_api(
        name="url-api",
        owner=group,
        system=system,
    )
    details = entity.api_details
    details.spec_source = SPEC_SOURCE_URL
    details.spec_url = "https://example.com/openapi.yaml"
    details.spec_content = STALE_CONTENT
    details.save()
    return details


def test_successful_refresh_updates_content_and_clears_failure_flag(url_api):
    with patch(SPEC_FETCH_PATCH_TARGET) as mock_get:
        mock_get.return_value = _fake_success("openapi: 3.0.1")
        refresh_spec_urls()

    url_api.refresh_from_db()
    assert url_api.spec_content == "openapi: 3.0.1"
    assert url_api.spec_resolve_failed is False
    assert url_api.spec_resolved_at is not None


def test_failed_fetch_preserves_last_good_content_and_flags_failure(url_api):
    with patch(SPEC_FETCH_PATCH_TARGET) as mock_get:
        mock_get.side_effect = SafeHttpError("boom")
        refresh_spec_urls()

    url_api.refresh_from_db()
    assert url_api.spec_content == STALE_CONTENT
    assert url_api.spec_resolve_failed is True


def test_empty_response_preserves_last_good_content_and_flags_failure(url_api):
    with patch(SPEC_FETCH_PATCH_TARGET) as mock_get:
        mock_get.return_value = _fake_success("   ")
        refresh_spec_urls()

    url_api.refresh_from_db()
    assert url_api.spec_content == STALE_CONTENT
    assert url_api.spec_resolve_failed is True


def test_unparseable_response_preserves_last_good_content_and_flags_failure(url_api):
    with patch(SPEC_FETCH_PATCH_TARGET) as mock_get:
        mock_get.return_value = _fake_success("not: yaml: [unterminated")
        refresh_spec_urls()

    url_api.refresh_from_db()
    assert url_api.spec_content == STALE_CONTENT
    assert url_api.spec_resolve_failed is True


def test_one_failing_api_does_not_block_refresh_of_others(group, system):
    failing_entity = create_api(name="failing-api", owner=group, system=system)
    failing = failing_entity.api_details
    failing.spec_source = SPEC_SOURCE_URL
    failing.spec_url = "https://example.com/broken.yaml"
    failing.save()

    healthy_entity = create_api(name="healthy-api", owner=group, system=system)
    healthy = healthy_entity.api_details
    healthy.spec_source = SPEC_SOURCE_URL
    healthy.spec_url = "https://example.com/healthy.yaml"
    healthy.save()

    def fake_get(url, **kwargs):
        if "broken" in url:
            raise SafeHttpError("boom")
        return _fake_success("openapi: 3.0.0", url=url)

    with patch(SPEC_FETCH_PATCH_TARGET, side_effect=fake_get):
        refresh_spec_urls()

    failing.refresh_from_db()
    healthy.refresh_from_db()
    assert failing.spec_resolve_failed is True
    assert healthy.spec_resolve_failed is False
    assert healthy.spec_content == "openapi: 3.0.0"


def test_refresh_skips_apis_not_sourced_from_a_url(group, system):
    inline_entity = create_api(name="inline-api", owner=group, system=system)
    inline_api = inline_entity.api_details
    inline_api.spec_source = SPEC_SOURCE_INLINE
    inline_api.spec_content = "openapi: 3.0.0"
    inline_api.save()

    with patch(SPEC_FETCH_PATCH_TARGET) as mock_get:
        refresh_spec_urls()

    mock_get.assert_not_called()
    inline_api.refresh_from_db()
    assert inline_api.spec_content == "openapi: 3.0.0"
