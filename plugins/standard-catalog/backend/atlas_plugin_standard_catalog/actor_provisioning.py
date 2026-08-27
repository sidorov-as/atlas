"""Standard Catalog implementation of the public Actor provisioning seam."""

from __future__ import annotations

from uuid import UUID

from atlas_plugin_api import (
    KIND_ACTOR,
    ActorProvisioningRequest,
    ActorProvisioningResult,
    ActorReference,
    get_catalog_entity_model,
)
from django.db import transaction
from django.utils.text import slugify

from .models import ActorDetails


def _reference(details: ActorDetails) -> ActorReference:
    return ActorReference(id=details.entity_id, name=details.entity.name)


class StandardCatalogActorProvisioningService:
    def resolve_for_principal(self, principal_id: int) -> ActorReference | None:
        details = (
            ActorDetails.objects.select_related("entity")
            .filter(account_id=principal_id)
            .first()
        )
        return _reference(details) if details is not None else None

    @transaction.atomic
    def ensure_for_principal(
        self, request: ActorProvisioningRequest
    ) -> ActorProvisioningResult:
        existing = (
            ActorDetails.objects.select_for_update()
            .select_related("entity")
            .filter(account_id=request.principal_id)
            .first()
        )
        if existing is not None:
            return ActorProvisioningResult(
                actor=_reference(existing), created=False, linked=False
            )

        entity_model = get_catalog_entity_model()
        base = (
            slugify(request.proposed_name)[:220] or f"principal-{request.principal_id}"
        )
        # Similar unlinked Actors are never claimed. A deterministic suffix
        # makes the new identity distinct while preserving retry idempotence.
        name = base
        if entity_model.objects.filter(kind=KIND_ACTOR, name__iexact=name).exists():
            name = f"{base[:220]}-{request.principal_id}"
        entity = entity_model.objects.create(kind=KIND_ACTOR, name=name)
        details = ActorDetails.objects.create(
            entity=entity,
            account_id=request.principal_id,
            display_name=request.display_name,
            email=request.email,
        )
        return ActorProvisioningResult(
            actor=_reference(details), created=True, linked=True
        )

    @transaction.atomic
    def link_existing(
        self, *, principal_id: int, actor_id: UUID, correlation_id: str
    ) -> ActorProvisioningResult:
        details = (
            ActorDetails.objects.select_for_update()
            .select_related("entity")
            .get(entity_id=actor_id)
        )
        if details.account_id not in (None, principal_id):
            raise ValueError("Actor is already linked to another Principal")
        linked = details.account_id is None
        if linked:
            details.account_id = principal_id
            details.save(update_fields=("account",))
        return ActorProvisioningResult(
            actor=_reference(details), created=False, linked=linked
        )

    @transaction.atomic
    def update_profile(
        self,
        *,
        principal_id: int,
        display_name: str | None,
        email: str | None,
    ) -> ActorReference | None:
        details = (
            ActorDetails.objects.select_for_update()
            .select_related("entity")
            .filter(account_id=principal_id)
            .first()
        )
        if details is None:
            return None
        fields: list[str] = []
        if display_name is not None and details.display_name != display_name:
            details.display_name = display_name
            fields.append("display_name")
        if email is not None and details.email != email:
            details.email = email
            fields.append("email")
        if fields:
            details.save(update_fields=fields)
        return _reference(details)


actor_provisioning_service = StandardCatalogActorProvisioningService()
