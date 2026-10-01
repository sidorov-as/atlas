"""Core Architecture Relationship Service.

Owns manual Architecture Relationship list/create/update/delete: manual-origin
creation only, YAML-origin mutation rejected, write permission checked on the
source entity, source kind limited to `INGESTIBLE_KINDS`, tags ensured. Both
the REST controllers (`server.apps.catalog.api.views`) and plugins (through
`atlas_plugin_api.get_architecture_relationship_service()`) call the singleton
below, so the rules live in one place.

The exception types are re-exported from `atlas_plugin_api` — canonical home
is the contract package, as with `entity_service.py`.
"""

from typing import Any

from atlas_plugin_api.architecture_relationships import (
    ArchitectureRelationshipNotFoundError,
    ArchitectureRelationshipReadOnlyError,
    ArchitectureRelationshipSourceKindError,
)
from django.db import transaction
from django.db.models import Q

from server.apps.catalog import refs
from server.apps.catalog.api.permissions import EntityWritePermission
from server.apps.catalog.models import (
    INGESTIBLE_KINDS,
    ArchitectureRelationship,
    CatalogEntity,
    ensure_tags_exist,
)

__all__ = [
    "ArchitectureRelationshipNotFoundError",
    "ArchitectureRelationshipReadOnlyError",
    "ArchitectureRelationshipService",
    "ArchitectureRelationshipSourceKindError",
    "architecture_relationship_service",
]

_UPDATABLE_FIELDS = ("label", "technology", "interaction_kind", "tags")


class ArchitectureRelationshipService:
    def get(self, relationship_id: int) -> ArchitectureRelationship:
        try:
            return ArchitectureRelationship.objects.select_related(
                "source", "target"
            ).get(pk=relationship_id)
        except ArchitectureRelationship.DoesNotExist:
            raise ArchitectureRelationshipNotFoundError(
                str(relationship_id)
            ) from None

    def list_for_entity(
        self, *, entity_ref: str
    ) -> list[ArchitectureRelationship]:
        entity = refs.resolve_ref(entity_ref)
        return list(
            ArchitectureRelationship.objects.filter(
                Q(source=entity) | Q(target=entity),
            )
            .select_related("source", "target")
            .order_by("id")
        )

    def create(
        self,
        *,
        source_ref: str,
        target_ref: str,
        label: str,
        technology: str = "",
        interaction_kind: str = "manual",
        tags: list[str] | None = None,
        actor: Any,
    ) -> ArchitectureRelationship:
        source = refs.resolve_ref(source_ref)
        if source.kind not in INGESTIBLE_KINDS:
            raise ArchitectureRelationshipSourceKindError(
                "Architecture relationship sources must be System, "
                "Component, Resource, or API entities"
            )
        EntityWritePermission.check_write(actor, source)
        target = refs.resolve_ref(target_ref)
        tags = tags or []
        with transaction.atomic():
            relationship = ArchitectureRelationship.objects.create(
                source=source,
                target=target,
                label=label,
                technology=technology,
                interaction_kind=interaction_kind,
                tags=tags,
                origin=ArchitectureRelationship.Origin.MANUAL,
            )
            ensure_tags_exist(tags)
        return relationship

    def update(
        self,
        *,
        relationship_id: int,
        fields: dict[str, Any],
        actor: Any,
    ) -> ArchitectureRelationship:
        """`fields` holds only the keys to change: `target` (a ref string),
        `label`, `technology`, `interaction_kind`, `tags`."""
        relationship = self._get_writable(relationship_id, actor)
        if "target" in fields:
            relationship.target = refs.resolve_ref(fields["target"])
        for field in _UPDATABLE_FIELDS:
            if field in fields:
                setattr(relationship, field, fields[field])
        with transaction.atomic():
            relationship.save()
            if "tags" in fields:
                ensure_tags_exist(fields["tags"])
        return relationship

    def delete(self, *, relationship_id: int, actor: Any) -> None:
        self._get_writable(relationship_id, actor).delete()

    def _get_writable(
        self, relationship_id: int, actor: Any
    ) -> ArchitectureRelationship:
        relationship = self.get(relationship_id)
        if relationship.origin == ArchitectureRelationship.Origin.YAML:
            raise ArchitectureRelationshipReadOnlyError(
                "YAML-origin architecture relationships are read-only"
            )
        source: CatalogEntity = relationship.source
        if source.kind not in INGESTIBLE_KINDS:
            raise ArchitectureRelationshipNotFoundError(str(relationship_id))
        EntityWritePermission.check_write(actor, source)
        return relationship


architecture_relationship_service = ArchitectureRelationshipService()
