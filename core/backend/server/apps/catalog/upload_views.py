"""Public `PUT /api/uploads/<token>` (`upload-tickets` spec): the ticket
token in the URL is the credential, so there is no session or
`Authorization` header. Every refusal to identify a ticket is the same 404.
"""

from typing import Any

from atlas_plugin_api import (
    UploadForbiddenError,
    UploadValidationError,
    get_upload_target,
)
from atlas_plugin_api.uploads import UnknownUploadTargetError
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services.upload_ticket_service import (
    check_entity_writable,
    consume_ticket,
    find_usable_ticket,
)

_READ_CHUNK = 64 * 1024


class _Rollback(Exception):
    def __init__(self, response: JsonResponse) -> None:
        self.response = response


def _error(status: int, message: str) -> JsonResponse:
    response = JsonResponse({"ok": False, "error": message}, status=status)
    response["Cache-Control"] = "no-store"
    return response


def _not_found() -> JsonResponse:
    return _error(404, "Not found")


def _read_capped(request: HttpRequest, limit: int) -> bytes | None:
    """The body, or `None` if it exceeds `limit`. Caps the bytes actually
    read, so a missing or false `Content-Length` cannot bypass the limit."""
    declared = request.META.get("CONTENT_LENGTH")
    if declared and declared.isdigit() and int(declared) > limit:
        return None
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = request.read(min(_READ_CHUNK, limit + 1 - total))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


@csrf_exempt
@require_http_methods(["PUT"])
def upload_view(request: HttpRequest, token: str) -> JsonResponse:
    ticket = find_usable_ticket(token)
    if ticket is None:
        return _not_found()
    try:
        target = get_upload_target(ticket.entity.kind, ticket.field)
    except UnknownUploadTargetError:
        return _not_found()

    body = _read_capped(request, min(ticket.max_bytes, target.max_bytes))
    if body is None:
        return _error(
            413, "Request body exceeds the size limit for this ticket"
        )

    summary: dict[str, Any] = {}
    try:
        with transaction.atomic():
            # Consume first: the conditional update takes the row lock, so a
            # concurrent upload blocks here and then finds it consumed. A
            # failure below rolls the consumption back with the write.
            if not consume_ticket(ticket):
                raise _Rollback(_not_found())
            try:
                check_entity_writable(ticket.user, ticket.entity)
                result = target.adapter.apply(
                    ticket.entity, body, ticket.params, ticket.user
                )
            except UploadForbiddenError as exc:
                raise _Rollback(_error(403, exc.reason)) from None
            except UploadValidationError as exc:
                raise _Rollback(_error(400, exc.reason)) from None
            summary = result.summary
    except _Rollback as rollback:
        return rollback.response

    response = JsonResponse({"ok": True, "summary": summary})
    response["Cache-Control"] = "no-store"
    return response
