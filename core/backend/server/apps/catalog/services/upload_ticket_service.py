"""Upload ticket issuance, lookup, and cleanup (`upload-tickets` spec).

The public `PUT` route (`server.apps.catalog.upload_views`) does the request
handling; this module owns everything that touches `UploadTicket` rows.
"""

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from atlas_plugin_api import (
    SOURCE_YAML,
    IssuedUploadTicket,
    UploadForbiddenError,
    get_policy_evaluator,
    get_upload_target,
)
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from server.apps.catalog.models import (
    CatalogEntity,
    PersonalAccessToken,
    UploadTicket,
)
from server.apps.catalog.models.upload_ticket import (
    generate_upload_token,
    hash_upload_token,
)

UPLOAD_PATH_PREFIX = "/api/uploads/"

YAML_MANAGED_MESSAGE = (
    "This entity is managed by catalog-info.yaml and is read-only"
)
NOT_OWNER_MESSAGE = "You are not a member of the owner Group"


def upload_path(token: str) -> str:
    return f"{UPLOAD_PATH_PREFIX}{token}"


def check_entity_writable(user: Any, entity: CatalogEntity) -> None:
    """The generic write guard every upload path repeats at issuance and at
    use: YAML-managed entities are read-only, and the user needs
    `<kind>.edit` on the entity."""
    if entity.source_kind == SOURCE_YAML:
        raise UploadForbiddenError(YAML_MANAGED_MESSAGE)
    if not get_policy_evaluator().check(user, f"{entity.kind}.edit", entity):
        raise UploadForbiddenError(NOT_OWNER_MESSAGE)


class UploadTicketServiceImpl:
    def issue(
        self,
        *,
        user: Any,
        token_id: int | None,
        scopes: frozenset[str],
        entity: CatalogEntity,
        field: str,
        params: Mapping[str, Any],
    ) -> IssuedUploadTicket:
        target = get_upload_target(entity.kind, field)
        if target.required_scope not in scopes:
            msg = (
                f"This token's scope does not permit {target.required_scope!r}"
            )
            raise UploadForbiddenError(msg)
        if token_id is None:
            msg = (
                "Upload tickets can only be issued with a Personal Access Token"
            )
            raise UploadForbiddenError(msg)
        check_entity_writable(user, entity)
        cleaned = target.adapter.validate_params(params)

        token = generate_upload_token()
        expires_at = timezone.now() + timedelta(
            seconds=settings.ATLAS_UPLOAD_TICKET_TTL_SECONDS
        )
        delete_stale_tickets()
        UploadTicket.objects.create(
            token_hash=hash_upload_token(token),
            entity=entity,
            field=field,
            params=cleaned,
            user=user,
            personal_access_token=PersonalAccessToken.objects.get(pk=token_id),
            expires_at=expires_at,
            max_bytes=target.max_bytes,
        )
        return IssuedUploadTicket(
            path=upload_path(token),
            expires_at=expires_at,
            max_bytes=target.max_bytes,
        )


upload_ticket_service = UploadTicketServiceImpl()


def find_usable_ticket(token: str) -> UploadTicket | None:
    """The ticket for `token` if unexpired, unconsumed, and its issuing PAT
    and owner are still valid; `None` otherwise (callers must not tell the
    reasons apart)."""
    ticket = (
        UploadTicket.objects.select_related(
            "entity", "user", "personal_access_token__owner"
        )
        .filter(token_hash=hash_upload_token(token))
        .first()
    )
    if ticket is None or not ticket.is_usable():
        return None
    return ticket


def consume_ticket(ticket: UploadTicket) -> bool:
    """Atomically mark `ticket` consumed; `False` if another request got
    there first. Call inside the same transaction as the write it guards."""
    return bool(
        UploadTicket.objects.filter(
            pk=ticket.pk, consumed_at__isnull=True
        ).update(consumed_at=timezone.now())
    )


def delete_stale_tickets() -> int:
    """Delete tickets expired or consumed longer ago than the retention
    period. Runs on every issuance rather than as a scheduled job: Core is
    always selected, and a core-declared job would make every startup read
    the job store."""
    cutoff = timezone.now() - timedelta(
        seconds=settings.ATLAS_UPLOAD_TICKET_RETENTION_SECONDS
    )
    deleted, _ = UploadTicket.objects.filter(
        Q(expires_at__lt=cutoff) | Q(consumed_at__lt=cutoff)
    ).delete()
    return deleted
