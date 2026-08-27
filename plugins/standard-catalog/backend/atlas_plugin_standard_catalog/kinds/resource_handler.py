"""`resource` Entity Kind handler."""

from typing import ClassVar

from atlas_plugin_api import (
    KIND_RESOURCE,
    KIND_SYSTEM,
    SCHEMA_HOST_V1,
    STATUS_ACTIVE,
    CatalogEntity,
    PurgeReference,
    ValidateDeleteError,
    refs,
)
from pydantic import BaseModel

from atlas_plugin_standard_catalog.api.schemas import (
    ResourceSpecIn,
    ResourceSpecOut,
    ResourceSpecPatch,
)
from atlas_plugin_standard_catalog.models import (
    ComponentDetails,
    ResourceDetails,
)


class ResourceKindHandler:
    kind_id = KIND_RESOURCE
    spec_schema: type[BaseModel] = ResourceSpecIn
    # Resources appear *inside* diagrams (as ComponentDb/ComponentQueue elements)
    # but aren't themselves diagram subjects.
    # Declares `schema.host.v1` unconditionally — every Resource,
    # regardless of its own `type`, may optionally carry a `DatabaseSchema`
    # Facet (scoping the
    # *capability* by a Resource's own `type` would require the capability
    # registry to understand per-instance state, which the kind-level
    # `provides=[...]` model doesn't support).
    provides: ClassVar[list] = [SCHEMA_HOST_V1]

    def create_details(self, entity: CatalogEntity, spec: ResourceSpecIn) -> None:
        ResourceDetails.objects.create(
            entity=entity,
            type=spec.type,
            system=(
                refs.resolve_ref(spec.system, expected_kind=KIND_SYSTEM)
                if spec.system
                else None
            ),
        )

    def update_details(self, entity: CatalogEntity, spec: ResourceSpecPatch) -> None:
        details = entity.resource_details
        fields = spec.model_fields_set
        if "type" in fields:
            details.type = spec.type
        if "system" in fields:
            details.system = (
                refs.resolve_ref(spec.system, expected_kind=KIND_SYSTEM)
                if spec.system
                else None
            )
        details.save()

    def serialize_details(self, entity: CatalogEntity) -> BaseModel:
        details = entity.resource_details
        return ResourceSpecOut(
            type=details.type,
            owner=entity.owner.ref,
            owner_id=entity.owner_id,
            system=details.system.ref if details.system_id else None,
            system_id=details.system_id,
        )

    def validate_delete(self, entity: CatalogEntity) -> None:
        # `ComponentDetails.depends_on` is a plain M2M — unlike the `system` FKs,
        # Django doesn't PROTECT it, so this is the only check standing between
        # a delete and silently orphaning dependent Components.
        dependents = ComponentDetails.objects.filter(depends_on=entity).count()
        if dependents:
            raise ValidateDeleteError(
                f"Cannot delete Resource {entity.name!r}: "
                f"{dependents} Component(s) still depend on it",
            )

    def is_deprecated(self, entity: CatalogEntity) -> bool:
        # A Resource carries no cosmetic lifecycle flag of its own.
        return False


def check_resource_purge_references(entity: CatalogEntity) -> list[PurgeReference]:
    """Purge scanner registered against `atlas_plugin_api.purge` (entity-removal-
    lifecycle spec: "Purge validation scans both FK-backed and ref-string-backed
    references") — the status-aware counterpart of `ResourceKindHandler.
    validate_delete`'s unconditional check above: a `removed` Component's
    `depends_on` link doesn't block the purge, it's cascaded away (`cascade`
    removes just that M2M row, not the Component itself); an `active`
    Component's does. Runs for every purge regardless of kind (self-filters
    on `entity.kind`) since the registry is shared across every purgeable kind.
    """
    if entity.kind != KIND_RESOURCE:
        return []
    references = []
    for details in ComponentDetails.objects.filter(depends_on=entity).select_related(
        "entity"
    ):
        component_entity = details.entity
        references.append(
            PurgeReference(
                label=f"Component {component_entity.name!r} (depends_on)",
                active=component_entity.status == STATUS_ACTIVE,
                cascade=lambda details=details: details.depends_on.remove(entity),
            ),
        )
    return references
