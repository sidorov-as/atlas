"""`system` Entity Kind handler (entity-kind-registry spec)."""

from typing import ClassVar

from atlas_plugin_api import (
    ARCHITECTURE_SUBJECT_V1,
    KIND_SYSTEM,
    CatalogEntity,
    ValidateDeleteError,
)
from pydantic import BaseModel

from atlas_plugin_standard_catalog.api.schemas import (
    SystemSpecIn,
    SystemSpecOut,
)
from atlas_plugin_standard_catalog.models import SystemDetails


class SystemKindHandler:
    kind_id = KIND_SYSTEM
    spec_schema: type[BaseModel] = SystemSpecIn
    provides: ClassVar[list] = [ARCHITECTURE_SUBJECT_V1]

    def create_details(self, entity: CatalogEntity, spec: BaseModel) -> None:
        # A System has no fields of its own beyond the common envelope + owner,
        # both already applied by the Entity Service — see `SystemDetails`.
        SystemDetails.objects.create(entity=entity)

    def update_details(self, entity: CatalogEntity, spec: BaseModel) -> None:
        pass

    def serialize_details(self, entity: CatalogEntity) -> BaseModel:
        return SystemSpecOut(owner=entity.owner.ref, owner_id=entity.owner_id)

    def validate_delete(self, entity: CatalogEntity) -> None:
        blockers = {
            "Components": entity.components.exists(),
            "Resources": entity.resources.exists(),
            "APIs": entity.apis.exists(),
            "Flows": entity.flows.exists(),
        }
        blocking = [name for name, present in blockers.items() if present]
        if blocking:
            raise ValidateDeleteError(
                f"Cannot delete System {entity.name!r}: still referenced by {', '.join(blocking)}",
            )

    def is_deprecated(self, entity: CatalogEntity) -> bool:
        # A System carries no cosmetic lifecycle flag of its own.
        return False
