"""Upload ticket issuance and the public `PUT /api/uploads/<token>` route
(`upload-tickets` spec), against a fake `(resource, notes)` target that
writes the body into the entity's description."""

import logging
from datetime import timedelta

import pytest
from atlas_plugin_api import (
    SOURCE_YAML,
    UnknownUploadTargetError,
    UploadForbiddenError,
    UploadResult,
    UploadTarget,
    UploadValidationError,
    register_upload_target,
)
from atlas_plugin_api import uploads as uploads_module
from django.utils import timezone

from server.apps.catalog.models import CatalogEntity, UploadTicket
from server.apps.catalog.services.pat_service import issue_personal_access_token
from server.apps.catalog.services.upload_ticket_service import (
    consume_ticket,
    delete_stale_tickets,
    upload_ticket_service,
)
from server.apps.catalog.tests.factories import create_resource

pytestmark = pytest.mark.django_db

SCOPE = "catalog:write"


class NotesAdapter:
    def validate_params(self, params):
        if params.get("mode", "ok") != "ok":
            raise UploadValidationError("unsupported mode")
        return {"mode": "ok"}

    def apply(self, entity, body, params, user):
        text = body.decode()
        if text == "bad":
            raise UploadValidationError("body is bad")
        if text == "forbidden":
            raise UploadForbiddenError("nope")
        CatalogEntity.objects.filter(pk=entity.pk).update(description=text)
        return UploadResult(summary={"chars": len(text)})


@pytest.fixture(autouse=True)
def notes_target(monkeypatch):
    monkeypatch.setattr(uploads_module, "_targets", {})
    register_upload_target(
        UploadTarget(
            kind="resource",
            field="notes",
            required_scope=SCOPE,
            max_bytes=16,
            adapter=NotesAdapter(),
        )
    )


@pytest.fixture
def resource(group):
    return create_resource(name="primary-db", owner=group)


@pytest.fixture
def pat(owner_user, owner_account):
    return issue_personal_access_token(owner=owner_account, scopes=[SCOPE])


def _issue(
    owner_account, pat, resource, field="notes", params=None, scopes=None
):
    return upload_ticket_service.issue(
        user=owner_account,
        token_id=pat.instance.pk,
        scopes=frozenset(scopes if scopes is not None else pat.instance.scopes),
        entity=resource,
        field=field,
        params=params or {},
    )


def _put(client, issued, body=b"hello"):
    return client.put(issued.path, data=body, content_type="text/plain")


def _description(resource):
    return CatalogEntity.objects.get(pk=resource.pk).description


def test_issue_returns_path_expiry_and_size_and_stores_only_a_hash(
    owner_account, pat, resource
):
    issued = _issue(owner_account, pat, resource)

    token = issued.path.removeprefix("/api/uploads/")
    ticket = UploadTicket.objects.get()
    assert issued.max_bytes == 16
    assert issued.expires_at > timezone.now()
    assert ticket.token_hash != token
    assert token not in ticket.token_hash
    assert len(token) >= 43  # 256 bits, url-safe base64


def test_issue_rejects_missing_scope(owner_account, pat, resource):
    with pytest.raises(UploadForbiddenError):
        _issue(owner_account, pat, resource, scopes=["catalog:read"])
    assert not UploadTicket.objects.exists()


def test_issue_rejects_a_caller_without_edit_permission(
    other_account, other_user, resource
):
    pat = issue_personal_access_token(owner=other_account, scopes=[SCOPE])

    with pytest.raises(UploadForbiddenError):
        _issue(other_account, pat, resource)
    assert not UploadTicket.objects.exists()


def test_issue_rejects_a_yaml_managed_entity(owner_account, pat, resource):
    CatalogEntity.objects.filter(pk=resource.pk).update(source_kind=SOURCE_YAML)
    resource.refresh_from_db()

    with pytest.raises(UploadForbiddenError, match="read-only"):
        _issue(owner_account, pat, resource)


def test_issue_rejects_an_unknown_target_naming_supported_fields(
    owner_account, pat, resource
):
    with pytest.raises(UnknownUploadTargetError, match="notes"):
        _issue(owner_account, pat, resource, field="nonsense")


def test_issue_rejects_invalid_params(owner_account, pat, resource):
    with pytest.raises(UploadValidationError):
        _issue(owner_account, pat, resource, params={"mode": "weird"})
    assert not UploadTicket.objects.exists()


def test_upload_applies_the_body_and_consumes_the_ticket(
    client, owner_account, pat, resource
):
    issued = _issue(owner_account, pat, resource)

    response = _put(client, issued)

    assert response.status_code == 200
    assert response.json() == {"ok": True, "summary": {"chars": 5}}
    assert _description(resource) == "hello"
    assert UploadTicket.objects.get().consumed_at is not None


def test_second_upload_is_a_404_and_writes_nothing(
    client, owner_account, pat, resource
):
    issued = _issue(owner_account, pat, resource)
    _put(client, issued, b"first")

    response = _put(client, issued, b"second")

    assert response.status_code == 404
    assert _description(resource) == "first"


def test_unknown_token_is_a_404(client):
    response = client.put(
        "/api/uploads/nope", data=b"x", content_type="text/plain"
    )

    assert response.status_code == 404


def test_failures_look_identical_to_unknown_tokens(
    client, owner_account, pat, resource
):
    unknown = client.put(
        "/api/uploads/nope", data=b"x", content_type="text/plain"
    )
    expired = _issue(owner_account, pat, resource)
    UploadTicket.objects.update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )

    response = _put(client, expired)

    assert response.status_code == 404
    assert response.content == unknown.content
    assert _description(resource) == ""


def test_retry_after_a_validation_failure_is_accepted(
    client, owner_account, pat, resource
):
    issued = _issue(owner_account, pat, resource)

    rejected = _put(client, issued, b"bad")
    assert rejected.status_code == 400
    assert rejected.json() == {"ok": False, "error": "body is bad"}
    assert UploadTicket.objects.get().consumed_at is None

    accepted = _put(client, issued, b"fixed")
    assert accepted.status_code == 200
    assert _description(resource) == "fixed"


def test_oversize_body_is_413_and_leaves_the_ticket_unused(
    client, owner_account, pat, resource
):
    issued = _issue(owner_account, pat, resource)

    response = _put(client, issued, b"x" * 17)

    assert response.status_code == 413
    assert _description(resource) == ""
    assert UploadTicket.objects.get().consumed_at is None


def test_permission_lost_after_issuance_rejects_without_consuming(
    client, owner_account, owner_user, group, pat, resource
):
    issued = _issue(owner_account, pat, resource)
    group.group_details.members.remove(owner_user)

    response = _put(client, issued)

    assert response.status_code == 403
    assert _description(resource) == ""
    assert UploadTicket.objects.get().consumed_at is None


def test_adapter_forbidden_leaves_the_ticket_unused(
    client, owner_account, pat, resource
):
    issued = _issue(owner_account, pat, resource)

    response = _put(client, issued, b"forbidden")

    assert response.status_code == 403
    assert UploadTicket.objects.get().consumed_at is None


def test_revoked_pat_ticket_is_rejected(client, owner_account, pat, resource):
    issued = _issue(owner_account, pat, resource)
    pat.instance.revoked_at = timezone.now()
    pat.instance.save()

    response = _put(client, issued)

    assert response.status_code == 404
    assert _description(resource) == ""


def test_expired_pat_ticket_is_rejected(client, owner_account, pat, resource):
    issued = _issue(owner_account, pat, resource)
    pat.instance.expires_at = timezone.now() - timedelta(seconds=1)
    pat.instance.save()

    response = _put(client, issued)

    assert response.status_code == 404
    assert _description(resource) == ""


def test_other_pats_tickets_are_unaffected_by_a_revocation(
    client, owner_account, pat, resource
):
    other_pat = issue_personal_access_token(owner=owner_account, scopes=[SCOPE])
    revoked = _issue(owner_account, pat, resource)
    surviving = _issue(owner_account, other_pat, resource)
    pat.instance.revoked_at = timezone.now()
    pat.instance.save()

    assert _put(client, revoked).status_code == 404
    assert _put(client, surviving).status_code == 200


def test_inactive_owner_ticket_is_rejected(
    client, owner_account, pat, resource
):
    issued = _issue(owner_account, pat, resource)
    owner_account.is_active = False
    owner_account.save()

    assert _put(client, issued).status_code == 404


def test_consume_is_conditional_so_only_one_concurrent_upload_wins(
    owner_account, pat, resource
):
    _issue(owner_account, pat, resource)
    ticket = UploadTicket.objects.get()

    assert consume_ticket(ticket) is True
    assert consume_ticket(ticket) is False


def test_token_is_redacted_from_log_records(owner_account, pat, resource):
    issued = _issue(owner_account, pat, resource)
    token = issued.path.removeprefix("/api/uploads/")

    from server.settings.components.logging import RedactUploadTokenFilter

    record = logging.LogRecord(
        "django.request",
        logging.WARNING,
        __file__,
        1,
        "%s: %s",
        ("Method Not Allowed", f"/api/uploads/{token}"),
        None,
    )
    RedactUploadTokenFilter().filter(record)

    assert token not in record.getMessage()
    assert "/api/uploads/[REDACTED]" in record.getMessage()


def test_django_loggers_use_the_redacting_handler():
    from server.settings.components.logging import LOGGING

    handler = LOGGING["handlers"]["console"]
    assert "redact_upload_token" in handler["filters"]
    for name in ("django", "django.server"):
        assert LOGGING["loggers"][name]["handlers"] == ["console"]


def test_cleanup_deletes_old_expired_and_consumed_tickets(
    owner_account, pat, resource
):
    old = timezone.now() - timedelta(days=30)
    for _ in range(3):
        _issue(owner_account, pat, resource)
    expired, consumed, live = UploadTicket.objects.order_by("pk")
    UploadTicket.objects.filter(pk=expired.pk).update(expires_at=old)
    UploadTicket.objects.filter(pk=consumed.pk).update(consumed_at=old)

    assert delete_stale_tickets() == 2

    assert list(UploadTicket.objects.all()) == [live]
