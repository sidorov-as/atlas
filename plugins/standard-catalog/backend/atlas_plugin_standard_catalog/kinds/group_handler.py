"""`group` (Team) Entity Kind handler.

Formalizes Team as a registered kind rather than a Django-admin-managed
side model — Group still has no public REST creation path (`entity-catalog`'s
"Group and User are read-only via API"), so this handler's `spec_schema`
is only ever exercised by Django admin (`admin.py`), never a controller.
"""

from typing import ClassVar

from atlas_plugin_api import (
    ARCHITECTURE_ACTOR_V1,
    KIND_ACTOR,
    KIND_GROUP,
    STATUS_ACTIVE,
    CatalogEntity,
    ValidateDeleteError,
    get_membership_service,
    refs,
)
from pydantic import BaseModel

from atlas_plugin_standard_catalog.api.schemas import GroupSpecIn, GroupSpecOut
from atlas_plugin_standard_catalog.models import GroupDetails


class GroupKindHandler:
    kind_id = KIND_GROUP
    spec_schema: type[BaseModel] = GroupSpecIn
    provides: ClassVar[list] = [ARCHITECTURE_ACTOR_V1]

    def create_details(self, entity: CatalogEntity, spec: GroupSpecIn) -> None:
        details = GroupDetails.objects.create(entity=entity, type=spec.type)
        get_membership_service().set_manual_memberships(
            details,
            (refs.resolve_ref(ref, expected_kind=KIND_ACTOR) for ref in spec.members),
        )

    def update_details(self, entity: CatalogEntity, spec: BaseModel) -> None:
        details = entity.group_details
        fields = spec.model_fields_set
        if "type" in fields:
            details.type = spec.type
            details.save()
        if "members" in fields:
            get_membership_service().set_manual_memberships(
                details,
                (
                    refs.resolve_ref(ref, expected_kind=KIND_ACTOR)
                    for ref in spec.members
                ),
            )

    def serialize_details(self, entity: CatalogEntity) -> BaseModel:
        details = entity.group_details
        service = get_membership_service()
        memberships = service.group_memberships(details)
        return GroupSpecOut(
            type=details.type,
            members=[row["actor"].ref for row in memberships if row["effective"]],
            membership_grants=[
                {
                    "entity": row["actor"].ref,
                    "effective": row["effective"],
                    "grants": row["grants"],
                }
                for row in memberships
            ],
        )

    def validate_delete(self, entity: CatalogEntity) -> None:
        # `catalog-auth` spec: an owner still owning `active` entities can't
        # be deleted; one whose owned entities are all `removed` may be
        # (base.py's `owner` FK is `SET_NULL`, not `PROTECT`, precisely so
        # this status-aware check — not a status-blind DB constraint —
        # is what gates it).
        active_owned = entity.owned_entities.filter(status=STATUS_ACTIVE)
        if active_owned.exists():
            names = ", ".join(active_owned.values_list("name", flat=True))
            raise ValidateDeleteError(
                f"Cannot delete Group {entity.name!r}: "
                f"still owns active entities: {names}",
            )

    def is_deprecated(self, entity: CatalogEntity) -> bool:
        # A Group carries no cosmetic lifecycle flag of its own.
        return False
