"""`user` (Actor) Entity Kind handler.

Actor is admin-managed and now ingestible (Team is not) but still has no public REST
creation
path — `spec_schema` is exercised by Django admin (`admin.py`) and by the
ingestion pipeline (`atlas_plugin_ingestion.upsert`), never a controller.
"""

from typing import ClassVar

from atlas_plugin_api import (
    ARCHITECTURE_ACTOR_V1,
    KIND_ACTOR,
    STATUS_ACTIVE,
    CatalogEntity,
    ValidateDeleteError,
    get_membership_service,
)
from pydantic import BaseModel

from atlas_plugin_standard_catalog.api.schemas import (
    ActorProfileOut,
    ActorSpecIn,
    ActorSpecOut,
)
from atlas_plugin_standard_catalog.models import ActorDetails


class ActorKindHandler:
    kind_id = KIND_ACTOR
    spec_schema: type[BaseModel] = ActorSpecIn
    provides: ClassVar[list] = [ARCHITECTURE_ACTOR_V1]

    def create_details(self, entity: CatalogEntity, spec: ActorSpecIn) -> None:
        ActorDetails.objects.create(
            entity=entity,
            display_name=spec.display_name,
            email=spec.email,
        )

    def update_details(self, entity: CatalogEntity, spec: BaseModel) -> None:
        details = entity.actor_details
        fields = spec.model_fields_set
        if "display_name" in fields:
            details.display_name = spec.display_name
        if "email" in fields:
            details.email = spec.email
        details.save()

    def serialize_details(self, entity: CatalogEntity) -> BaseModel:
        details = entity.actor_details
        memberships = get_membership_service().actor_memberships(entity)
        return ActorSpecOut(
            member_of=[row["group"].ref for row in memberships if row["effective"]],
            membership_grants=[
                {
                    "entity": row["group"].ref,
                    "effective": row["effective"],
                    "grants": row["grants"],
                }
                for row in memberships
            ],
            profile=ActorProfileOut(
                display_name=details.display_name,
                email=details.email,
            ),
        )

    def validate_delete(self, entity: CatalogEntity) -> None:
        # `GroupDetails.members` and Architecture Relationship endpoints are
        # plain M2M/FK without PROTECT — but nothing today models "an Actor
        # can't be deleted while still a Group member or relationship
        # endpoint" as a hard rule, matching the pre-existing (Django-admin-
        # only) delete behavior for `User`/`ActorDetails`. `owner` is the one
        # exception: an Actor can itself be an entity's `owner` (base.py's
        # `owner` FK isn't kind-restricted), so it's subject to the same
        # owner protected-reference rule as Group (see
        # `group_handler.validate_delete`'s longer explanation).
        active_owned = entity.owned_entities.filter(status=STATUS_ACTIVE)
        if active_owned.exists():
            names = ", ".join(active_owned.values_list("name", flat=True))
            raise ValidateDeleteError(
                f"Cannot delete Actor {entity.name!r}: "
                f"still owns active entities: {names}",
            )

    def is_deprecated(self, entity: CatalogEntity) -> bool:
        # An Actor carries no cosmetic lifecycle flag of its own.
        return False
