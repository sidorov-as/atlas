"""`component` Entity Kind handler."""

from typing import ClassVar

from atlas_plugin_api import (
    ARCHITECTURE_SUBJECT_V1,
    KIND_API,
    KIND_COMPONENT,
    KIND_RESOURCE,
    KIND_SYSTEM,
    STATUS_ACTIVE,
    CatalogEntity,
    PurgeReference,
    ValidateDeleteError,
    refs,
)
from django.db.models import Q
from pydantic import BaseModel

from atlas_plugin_standard_catalog.api.schemas import (
    ComponentSpecIn,
    ComponentSpecOut,
    ComponentSpecPatch,
)
from atlas_plugin_standard_catalog.models import ComponentDetails


class ComponentKindHandler:
    kind_id = KIND_COMPONENT
    spec_schema: type[BaseModel] = ComponentSpecIn
    patch_schema: type[BaseModel] = ComponentSpecPatch
    provides: ClassVar[list] = [ARCHITECTURE_SUBJECT_V1]

    def create_details(self, entity: CatalogEntity, spec: ComponentSpecIn) -> None:
        details = ComponentDetails.objects.create(
            entity=entity,
            type=spec.type,
            lifecycle=spec.lifecycle,
            system=refs.resolve_ref(spec.system, expected_kind=KIND_SYSTEM),
        )
        details.provides_apis.set(
            refs.resolve_ref(ref, expected_kind=KIND_API) for ref in spec.provides_apis
        )
        details.consumes_apis.set(
            refs.resolve_ref(ref, expected_kind=KIND_API) for ref in spec.consumes_apis
        )
        details.depends_on.set(
            refs.resolve_ref(ref, expected_kind=KIND_RESOURCE)
            for ref in spec.depends_on
        )

    def update_details(self, entity: CatalogEntity, spec: ComponentSpecPatch) -> None:
        details = entity.component_details
        fields = spec.model_fields_set
        if "type" in fields:
            details.type = spec.type
        if "lifecycle" in fields:
            details.lifecycle = spec.lifecycle
        if "system" in fields:
            details.system = refs.resolve_ref(spec.system, expected_kind=KIND_SYSTEM)
        details.save()
        if "provides_apis" in fields:
            details.provides_apis.set(
                refs.resolve_ref(ref, expected_kind=KIND_API)
                for ref in spec.provides_apis
            )
        if "consumes_apis" in fields:
            details.consumes_apis.set(
                refs.resolve_ref(ref, expected_kind=KIND_API)
                for ref in spec.consumes_apis
            )
        if "depends_on" in fields:
            details.depends_on.set(
                refs.resolve_ref(ref, expected_kind=KIND_RESOURCE)
                for ref in spec.depends_on
            )

    def serialize_details(self, entity: CatalogEntity) -> BaseModel:
        details = entity.component_details
        return ComponentSpecOut(
            type=details.type,
            lifecycle=details.lifecycle,
            owner=entity.owner.ref,
            owner_id=entity.owner_id,
            system=details.system.ref,
            system_id=details.system_id,
            provides_apis=[api.ref for api in details.provides_apis.all()],
            consumes_apis=[api.ref for api in details.consumes_apis.all()],
            depends_on=[resource.ref for resource in details.depends_on.all()],
        )

    def validate_delete(self, entity: CatalogEntity) -> None:
        # Nothing currently references a Component by FK/M2M (ArchitectureRelationship
        # CASCADEs, not PROTECTs) — deleting one is always allowed.
        pass

    def is_deprecated(self, entity: CatalogEntity) -> bool:
        return entity.component_details.lifecycle == "deprecated"


def check_component_references_api(entity: CatalogEntity) -> None:
    """Delete guard registered against `atlas_plugin_apis`'s
    `atlas.apis.delete_guards` extension point — `ComponentDetails.provides_apis`/
    `consumes_apis` are plain M2Ms, not PROTECTed by the DB, so this is the
    only check standing between deleting an API and silently orphaning
    dependent Components. Registered here (see `kinds/__init__.py`) instead
    of `atlas_plugin_apis` importing `ComponentDetails` directly.
    """
    dependents = (
        ComponentDetails.objects.filter(
            Q(provides_apis=entity) | Q(consumes_apis=entity)
        )
        .distinct()
        .count()
    )
    if dependents:
        raise ValidateDeleteError(
            f"Cannot delete API {entity.name!r}: "
            f"{dependents} Component(s) still reference it",
        )


def check_api_purge_references(entity: CatalogEntity) -> list[PurgeReference]:
    """Purge scanner registered against `atlas_plugin_api.purge` — the status-aware
    counterpart of `check_component_references_api`'s unconditional delete guard
    above: a `removed` Component's `provides_apis`/`consumes_apis` link doesn't
    block the purge, it's cascaded away; an `active` Component's does. Removes
    from both M2Ms unconditionally in `cascade` rather than tracking which one
    matched — removing an entity that isn't a member of a M2M is a harmless
    no-op. Self-filters on `entity.kind` (see `check_resource_purge_references`).
    """
    if entity.kind != KIND_API:
        return []
    references = []
    dependents = (
        ComponentDetails.objects.filter(
            Q(provides_apis=entity) | Q(consumes_apis=entity)
        )
        .distinct()
        .select_related("entity")
    )
    for details in dependents:
        component_entity = details.entity
        references.append(
            PurgeReference(
                label=f"Component {component_entity.name!r} (provides/consumes)",
                active=component_entity.status == STATUS_ACTIVE,
                cascade=lambda details=details: (
                    details.provides_apis.remove(entity),
                    details.consumes_apis.remove(entity),
                ),
            ),
        )
    return references
