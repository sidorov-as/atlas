"""`request_attach` (`mcp-upload-tools` / `mcp-plugin` specs). Issuance itself
(scope, RBAC, YAML-managed) is Core's and tested there; these tests bind a
stub ticket service to check what this controller passes in and how it maps
errors."""

from datetime import UTC, datetime

import atlas_plugin_api.uploads as uploads_module
import pytest
from atlas_plugin_api import (
    IssuedUploadTicket,
    UnknownUploadTargetError,
    UploadForbiddenError,
    UploadValidationError,
    bind_upload_ticket_service,
)
from server.apps.catalog.tests.factories import create_api

from atlas_plugin_mcp.api.openapi import build_openapi_schema

pytestmark = pytest.mark.django_db

_URL = "/api/plugins/atlas.mcp/uploads/"
_EXPIRES = datetime(2030, 1, 1, tzinfo=UTC)


class _StubTicketService:
    def __init__(self):
        self.calls = []
        self.error = None

    def issue(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return IssuedUploadTicket(
            path="/api/uploads/secret-token", expires_at=_EXPIRES, max_bytes=1234
        )


@pytest.fixture
def ticket_service():
    previous = uploads_module._ticket_service
    stub = _StubTicketService()
    bind_upload_ticket_service(stub)
    yield stub
    uploads_module._ticket_service = previous


@pytest.fixture
def api(group, system):
    return create_api(name="booking", owner=group, system=system)


def _post(dmr_client, header, body):
    return dmr_client.post(_URL, body, content_type="application/json", **header)


def _body(**extra):
    return {"entity": "api:booking", "field": "spec", **extra}


def test_returns_the_ticket_and_passes_the_pats_identity(
    dmr_client, api, ticket_service, write_scoped_pat_auth_header, owner_account
):
    response = _post(dmr_client, write_scoped_pat_auth_header, _body())

    assert response.status_code == 200
    assert response.json() == {
        "entity": api.ref,
        "field": "spec",
        "uploadPath": "/api/uploads/secret-token",
        "expiresAt": "2030-01-01T00:00:00Z",
        "maxBytes": 1234,
    }
    call = ticket_service.calls[0]
    assert call["entity"].pk == api.pk
    assert call["field"] == "spec"
    assert call["user"] == owner_account
    assert "catalog:write" in call["scopes"]


def test_target_params_are_passed_through(
    dmr_client, api, ticket_service, write_scoped_pat_auth_header
):
    _post(
        dmr_client,
        write_scoped_pat_auth_header,
        _body(params={"dialect": "mysql"}),
    )

    assert ticket_service.calls[0]["params"] == {"dialect": "mysql"}


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (UploadForbiddenError("scope"), 403),
        (UploadValidationError("bad dialect"), 400),
        (UnknownUploadTargetError("api", "nope", ("spec",)), 400),
    ],
)
def test_issuance_errors_are_mapped(
    dmr_client, api, ticket_service, write_scoped_pat_auth_header, error, status
):
    ticket_service.error = error

    response = _post(dmr_client, write_scoped_pat_auth_header, _body())

    assert response.status_code == status


def test_unknown_entity_is_404(
    dmr_client, api, ticket_service, write_scoped_pat_auth_header
):
    response = _post(
        dmr_client,
        write_scoped_pat_auth_header,
        {"entity": "api:nope", "field": "spec"},
    )

    assert response.status_code == 404
    assert ticket_service.calls == []


def test_unknown_keys_are_rejected(
    dmr_client, api, ticket_service, write_scoped_pat_auth_header
):
    response = _post(dmr_client, write_scoped_pat_auth_header, _body(fiel="x"))

    assert response.status_code in (400, 422)
    assert ticket_service.calls == []


def test_a_pat_is_required(dmr_client, api, ticket_service):
    response = dmr_client.post(_URL, _body(), content_type="application/json")

    assert response.status_code in (401, 403)


def test_operation_is_present_with_a_registered_target():
    paths = build_openapi_schema().paths or {}

    assert any(path.endswith("/uploads/") for path in paths)


def test_operation_is_absent_without_any_target(monkeypatch):
    monkeypatch.setattr(uploads_module, "_targets", {})

    paths = build_openapi_schema().paths or {}

    assert not any("uploads" in path for path in paths)


def test_the_raw_put_is_not_part_of_the_mcp_document():
    paths = build_openapi_schema().paths or {}

    assert not any("/api/uploads/" in path for path in paths)
    assert not any(item.put for item in paths.values())
