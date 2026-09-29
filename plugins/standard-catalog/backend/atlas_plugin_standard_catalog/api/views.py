"""Entity CRUD controllers for System, Component, Resource, Team (Group), and
Actor — split out of
`server.apps.catalog.api.views`. Group and
Actor only get list/detail GET; they're admin/ingestion-managed, never
user-creatable via the public REST API.

Writes (create/update/delete) go exclusively through the core `EntityService`
via the registered kind handlers in
`atlas_plugin_standard_catalog.kinds` — this module owns request parsing,
response shaping, and the `_get_<kind>` 404/kind guard, not persistence.
"""

import logging
from http import HTTPStatus
from typing import Any

from atlas_plugin_api import (
    API_VERSION,
    FORBIDDEN_RESPONSE,
    KIND_ACTOR,
    KIND_COMPONENT,
    KIND_GROUP,
    KIND_RESOURCE,
    KIND_SYSTEM,
    AdoptIn,
    CatalogEntity,
    EntityPath,
    HistoryRecordOut,
    LinkSchema,
    ListFilters,
    PageOut,
    PaginatedOut,
    RelationOut,
    SessionAuth,
    adopt,
    blocked_by,
    blocked_by_reason,
    entity_capabilities,
    entity_permissions,
    filter_by_field,
    filter_by_owner,
    filter_by_search,
    filter_by_status,
    filter_by_system,
    filter_by_tags_overlap,
    get_catalog_entity_model,
    get_entity_service,
    get_membership_service,
    history_out,
    ingested_from,
    metadata_out,
    purge_entity,
    relations_out,
    remove_entity,
    revive_entity,
    spec_owner_ref,
)
from atlas_plugin_api.controllers import AtlasController
from django.core.paginator import Paginator
from dmr import Body, Path, Query, modify
from dmr.errors import ErrorType, format_error
from dmr.response import APIError
from pydantic import ValidationError

from .schemas import (
    ActorOut,
    ActorProfileOut,
    ActorSpecOut,
    ComponentIn,
    ComponentOut,
    ComponentPatch,
    ComponentSpecOut,
    GroupOut,
    GroupSpecOut,
    ResourceIn,
    ResourceOut,
    ResourcePatch,
    ResourceSpecOut,
    SystemDocumentLinksQuery,
    SystemIn,
    SystemOut,
    SystemPatch,
    SystemSpecOut,
)

logger = logging.getLogger("atlas_plugin_standard_catalog")


def _not_found(message: str) -> APIError:
    return APIError(
        format_error(message, error_type=ErrorType.not_found),
        status_code=HTTPStatus.NOT_FOUND,
    )


# --- System ---------------------------------------------------------------


def _system_out(instance: CatalogEntity, user: Any = None) -> SystemOut:
    return SystemOut(
        id=instance.id,
        api_version=API_VERSION,
        metadata=metadata_out(instance),
        spec=SystemSpecOut(owner=instance.owner.ref, owner_id=instance.owner.id),
        status=instance.status,
        ingested_from=ingested_from(instance),
        blocked_by=blocked_by(instance),
        blocked_by_reason=blocked_by_reason(instance),
        capabilities=entity_capabilities(instance),
        permissions=entity_permissions(instance, user) if user else None,
    )


def _get_system(pk) -> CatalogEntity:
    catalog_entity_model = get_catalog_entity_model()
    try:
        return catalog_entity_model.objects.select_related(
            "owner",
            "ingested_from",
            "system_details",
        ).get(pk=pk, kind=KIND_SYSTEM)
    except catalog_entity_model.DoesNotExist:
        raise _not_found("System not found") from None


class SystemListController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_query: Query[ListFilters]) -> PaginatedOut[SystemOut]:
        queryset = (
            get_catalog_entity_model()
            .objects.filter(kind=KIND_SYSTEM)
            .select_related(
                "owner",
                "ingested_from",
                "system_details",
            )
        )
        queryset = filter_by_owner(queryset, parsed_query.owner)
        queryset = filter_by_search(queryset, parsed_query.q)
        queryset = filter_by_tags_overlap(queryset, parsed_query.tags)
        queryset = filter_by_status(queryset, parsed_query.status)
        page = Paginator(
            queryset.order_by(parsed_query.sort, "id"), parsed_query.page_size
        ).page(parsed_query.page)
        return PaginatedOut(
            count=page.paginator.count,
            num_pages=page.paginator.num_pages,
            per_page=page.paginator.per_page,
            page=PageOut(
                number=page.number,
                object_list=[_system_out(instance) for instance in page.object_list],
            ),
        )

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_body: Body[SystemIn]) -> SystemOut:
        entity = get_entity_service().create(
            kind_id=KIND_SYSTEM,
            owner_ref=parsed_body.spec.owner,
            metadata=parsed_body.metadata,
            spec=parsed_body.spec,
            actor=self.request.user,
        )
        return _system_out(entity, self.request.user)


class SystemDetailController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> SystemOut:
        return _system_out(_get_system(parsed_path.id), self.request.user)

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def patch(
        self,
        parsed_path: Path[EntityPath],
        parsed_body: Body[SystemPatch],
    ) -> SystemOut:
        _get_system(parsed_path.id)
        entity = get_entity_service().update(
            entity_id=parsed_path.id,
            owner_ref=spec_owner_ref(parsed_body.spec),
            metadata=parsed_body.metadata,
            spec=parsed_body.spec,
            actor=self.request.user,
        )
        return _system_out(entity, self.request.user)

    # No `delete`: retired in favor of Remove -> Purge as the sole destructive path (D14).


class SystemDocumentLinksController(AtlasController):
    """Read-only, declaration-ordered view of one System's metadata links."""

    auth = (SessionAuth(),)

    def get(
        self,
        parsed_path: Path[EntityPath],
        parsed_query: Query[SystemDocumentLinksQuery],
    ) -> PaginatedOut[LinkSchema]:
        links = [LinkSchema(**link) for link in _get_system(parsed_path.id).links]
        if parsed_query.q:
            query = parsed_query.q.casefold()
            links = [
                link
                for link in links
                if query in link.title.casefold()
                or query in link.description.casefold()
            ]
        page = Paginator(links, parsed_query.page_size).page(parsed_query.page)
        return PaginatedOut(
            count=page.paginator.count,
            num_pages=page.paginator.num_pages,
            per_page=page.paginator.per_page,
            page=PageOut(number=page.number, object_list=list(page.object_list)),
        )


class SystemRelationsController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> list[RelationOut]:
        return relations_out(_get_system(parsed_path.id))


class SystemHistoryController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> list[HistoryRecordOut]:
        return history_out(_get_system(parsed_path.id))


class SystemAdoptController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.OK, extra_responses=[FORBIDDEN_RESPONSE])
    def post(
        self, parsed_path: Path[EntityPath], parsed_body: Body[AdoptIn]
    ) -> SystemOut:
        instance = _get_system(parsed_path.id)
        adopt(instance, self.request, parsed_body)
        return _system_out(instance, self.request.user)


class SystemRemoveController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.OK, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath]) -> SystemOut:
        _get_system(parsed_path.id)
        entity = remove_entity(parsed_path.id, self.request.user)
        return _system_out(entity, self.request.user)


class SystemReviveController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.OK, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath]) -> SystemOut:
        _get_system(parsed_path.id)
        entity = revive_entity(parsed_path.id, self.request.user)
        return _system_out(entity, self.request.user)


class SystemPurgeController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.NO_CONTENT, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath]) -> None:
        _get_system(parsed_path.id)
        purge_entity(parsed_path.id, self.request.user)


# --- Component --------------------------------------------------------------


def _component_out(instance: CatalogEntity, user: Any = None) -> ComponentOut:
    details = instance.component_details
    return ComponentOut(
        id=instance.id,
        api_version=API_VERSION,
        metadata=metadata_out(instance),
        spec=ComponentSpecOut(
            type=details.type,
            lifecycle=details.lifecycle,
            owner=instance.owner.ref,
            owner_id=instance.owner.id,
            system=details.system.ref,
            system_id=details.system.id,
            provides_apis=[api.ref for api in details.provides_apis.all()],
            consumes_apis=[api.ref for api in details.consumes_apis.all()],
            depends_on=[resource.ref for resource in details.depends_on.all()],
        ),
        status=instance.status,
        ingested_from=ingested_from(instance),
        blocked_by=blocked_by(instance),
        blocked_by_reason=blocked_by_reason(instance),
        capabilities=entity_capabilities(instance),
        permissions=entity_permissions(instance, user) if user else None,
    )


def _get_component(pk) -> CatalogEntity:
    catalog_entity_model = get_catalog_entity_model()
    try:
        return (
            catalog_entity_model.objects.select_related(
                "owner",
                "ingested_from",
                "component_details",
                "component_details__system",
            )
            .prefetch_related(
                "component_details__provides_apis",
                "component_details__consumes_apis",
                "component_details__depends_on",
            )
            .get(pk=pk, kind=KIND_COMPONENT)
        )
    except catalog_entity_model.DoesNotExist:
        raise _not_found("Component not found") from None


class ComponentListController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_query: Query[ListFilters]) -> PaginatedOut[ComponentOut]:
        queryset = (
            get_catalog_entity_model()
            .objects.filter(kind=KIND_COMPONENT)
            .select_related(
                "owner",
                "ingested_from",
                "component_details",
                "component_details__system",
            )
            .prefetch_related(
                "component_details__provides_apis",
                "component_details__consumes_apis",
                "component_details__depends_on",
            )
        )
        queryset = filter_by_owner(queryset, parsed_query.owner)
        queryset = filter_by_system(
            queryset, parsed_query.system, prefix="component_details__"
        )
        queryset = filter_by_field(
            queryset, "type", parsed_query.type, prefix="component_details__"
        )
        queryset = filter_by_field(
            queryset, "lifecycle", parsed_query.lifecycle, prefix="component_details__"
        )
        queryset = filter_by_search(queryset, parsed_query.q)
        queryset = filter_by_tags_overlap(queryset, parsed_query.tags)
        queryset = filter_by_status(queryset, parsed_query.status)
        page = Paginator(
            queryset.order_by(parsed_query.sort, "id"), parsed_query.page_size
        ).page(parsed_query.page)
        return PaginatedOut(
            count=page.paginator.count,
            num_pages=page.paginator.num_pages,
            per_page=page.paginator.per_page,
            page=PageOut(
                number=page.number,
                object_list=[_component_out(instance) for instance in page.object_list],
            ),
        )

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_body: Body[ComponentIn]) -> ComponentOut:
        entity = get_entity_service().create(
            kind_id=KIND_COMPONENT,
            owner_ref=parsed_body.spec.owner,
            metadata=parsed_body.metadata,
            spec=parsed_body.spec,
            actor=self.request.user,
        )
        return _component_out(entity, self.request.user)


class ComponentDetailController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> ComponentOut:
        return _component_out(_get_component(parsed_path.id), self.request.user)

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def patch(
        self,
        parsed_path: Path[EntityPath],
        parsed_body: Body[ComponentPatch],
    ) -> ComponentOut:
        _get_component(parsed_path.id)
        entity = get_entity_service().update(
            entity_id=parsed_path.id,
            owner_ref=spec_owner_ref(parsed_body.spec),
            metadata=parsed_body.metadata,
            spec=parsed_body.spec,
            actor=self.request.user,
        )
        return _component_out(entity, self.request.user)

    # No `delete`: retired in favor of Remove -> Purge as the sole destructive path (D14).


class ComponentRelationsController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> list[RelationOut]:
        return relations_out(_get_component(parsed_path.id))


class ComponentHistoryController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> list[HistoryRecordOut]:
        return history_out(_get_component(parsed_path.id))


class ComponentAdoptController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.OK, extra_responses=[FORBIDDEN_RESPONSE])
    def post(
        self, parsed_path: Path[EntityPath], parsed_body: Body[AdoptIn]
    ) -> ComponentOut:
        instance = _get_component(parsed_path.id)
        adopt(instance, self.request, parsed_body)
        return _component_out(instance, self.request.user)


class ComponentRemoveController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.OK, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath]) -> ComponentOut:
        _get_component(parsed_path.id)
        entity = remove_entity(parsed_path.id, self.request.user)
        return _component_out(entity, self.request.user)


class ComponentReviveController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.OK, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath]) -> ComponentOut:
        _get_component(parsed_path.id)
        entity = revive_entity(parsed_path.id, self.request.user)
        return _component_out(entity, self.request.user)


class ComponentPurgeController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.NO_CONTENT, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath]) -> None:
        _get_component(parsed_path.id)
        purge_entity(parsed_path.id, self.request.user)


# --- Resource -------------------------------------------------------------


def _resource_out(instance: CatalogEntity, user: Any = None) -> ResourceOut:
    details = instance.resource_details
    return ResourceOut(
        id=instance.id,
        api_version=API_VERSION,
        metadata=metadata_out(instance),
        spec=ResourceSpecOut(
            type=details.type,
            owner=instance.owner.ref,
            owner_id=instance.owner.id,
            system=details.system.ref if details.system_id else None,
            system_id=details.system_id,
        ),
        status=instance.status,
        ingested_from=ingested_from(instance),
        blocked_by=blocked_by(instance),
        blocked_by_reason=blocked_by_reason(instance),
        capabilities=entity_capabilities(instance),
        permissions=entity_permissions(instance, user) if user else None,
    )


def _get_resource(pk) -> CatalogEntity:
    catalog_entity_model = get_catalog_entity_model()
    try:
        return catalog_entity_model.objects.select_related(
            "owner",
            "ingested_from",
            "resource_details",
            "resource_details__system",
        ).get(pk=pk, kind=KIND_RESOURCE)
    except catalog_entity_model.DoesNotExist:
        raise _not_found("Resource not found") from None


class ResourceListController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_query: Query[ListFilters]) -> PaginatedOut[ResourceOut]:
        queryset = (
            get_catalog_entity_model()
            .objects.filter(kind=KIND_RESOURCE)
            .select_related(
                "owner",
                "ingested_from",
                "resource_details",
                "resource_details__system",
            )
        )
        queryset = filter_by_owner(queryset, parsed_query.owner)
        queryset = filter_by_system(
            queryset, parsed_query.system, prefix="resource_details__"
        )
        queryset = filter_by_field(
            queryset, "type", parsed_query.type, prefix="resource_details__"
        )
        queryset = filter_by_search(queryset, parsed_query.q)
        queryset = filter_by_tags_overlap(queryset, parsed_query.tags)
        queryset = filter_by_status(queryset, parsed_query.status)
        page = Paginator(
            queryset.order_by(parsed_query.sort, "id"), parsed_query.page_size
        ).page(parsed_query.page)
        return PaginatedOut(
            count=page.paginator.count,
            num_pages=page.paginator.num_pages,
            per_page=page.paginator.per_page,
            page=PageOut(
                number=page.number,
                object_list=[_resource_out(instance) for instance in page.object_list],
            ),
        )

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_body: Body[ResourceIn]) -> ResourceOut:
        entity = get_entity_service().create(
            kind_id=KIND_RESOURCE,
            owner_ref=parsed_body.spec.owner,
            metadata=parsed_body.metadata,
            spec=parsed_body.spec,
            actor=self.request.user,
        )
        return _resource_out(entity, self.request.user)


class ResourceDetailController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> ResourceOut:
        return _resource_out(_get_resource(parsed_path.id), self.request.user)

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def patch(
        self,
        parsed_path: Path[EntityPath],
        parsed_body: Body[ResourcePatch],
    ) -> ResourceOut:
        _get_resource(parsed_path.id)
        entity = get_entity_service().update(
            entity_id=parsed_path.id,
            owner_ref=spec_owner_ref(parsed_body.spec),
            metadata=parsed_body.metadata,
            spec=parsed_body.spec,
            actor=self.request.user,
        )
        return _resource_out(entity, self.request.user)

    # No `delete`: retired in favor of Remove -> Purge as the sole destructive path (D14).


class ResourceRelationsController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> list[RelationOut]:
        return relations_out(_get_resource(parsed_path.id))


class ResourceHistoryController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> list[HistoryRecordOut]:
        return history_out(_get_resource(parsed_path.id))


class ResourceAdoptController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.OK, extra_responses=[FORBIDDEN_RESPONSE])
    def post(
        self, parsed_path: Path[EntityPath], parsed_body: Body[AdoptIn]
    ) -> ResourceOut:
        instance = _get_resource(parsed_path.id)
        adopt(instance, self.request, parsed_body)
        return _resource_out(instance, self.request.user)


class ResourceRemoveController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.OK, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath]) -> ResourceOut:
        _get_resource(parsed_path.id)
        entity = remove_entity(parsed_path.id, self.request.user)
        return _resource_out(entity, self.request.user)


class ResourceReviveController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.OK, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath]) -> ResourceOut:
        _get_resource(parsed_path.id)
        entity = revive_entity(parsed_path.id, self.request.user)
        return _resource_out(entity, self.request.user)


class ResourcePurgeController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.NO_CONTENT, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath]) -> None:
        _get_resource(parsed_path.id)
        purge_entity(parsed_path.id, self.request.user)


# --- Group / Actor (read-only via public API) -------------------------------


def _group_out(instance: CatalogEntity) -> GroupOut:
    details = instance.group_details
    memberships = get_membership_service().group_memberships(details)
    return GroupOut(
        id=instance.id,
        metadata=metadata_out(instance),
        spec=GroupSpecOut(
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
        ),
        capabilities=entity_capabilities(instance),
    )


def _actor_out(instance: CatalogEntity) -> ActorOut:
    details = instance.actor_details
    memberships = get_membership_service().actor_memberships(instance)
    return ActorOut(
        id=instance.id,
        metadata=metadata_out(instance),
        spec=ActorSpecOut(
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
                display_name=details.display_name, email=details.email
            ),
        ),
        capabilities=entity_capabilities(instance),
    )


class GroupListController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_query: Query[ListFilters]) -> PaginatedOut[GroupOut]:
        queryset = (
            get_catalog_entity_model()
            .objects.filter(kind=KIND_GROUP)
            .select_related(
                "group_details",
            )
        )
        queryset = filter_by_field(
            queryset, "type", parsed_query.type, prefix="group_details__"
        )
        queryset = filter_by_search(queryset, parsed_query.q)
        groups = []
        page = Paginator(
            queryset.order_by(parsed_query.sort, "id"), parsed_query.page_size
        ).page(parsed_query.page)
        for instance in page.object_list:
            try:
                groups.append(_group_out(instance))
            except ValidationError:
                logger.warning(
                    "Skipping Group %s from list: invalid data",
                    instance.pk,
                    exc_info=True,
                )
        return PaginatedOut(
            count=page.paginator.count,
            num_pages=page.paginator.num_pages,
            per_page=page.paginator.per_page,
            page=PageOut(number=page.number, object_list=groups),
        )


def _get_group(pk) -> CatalogEntity:
    catalog_entity_model = get_catalog_entity_model()
    try:
        return catalog_entity_model.objects.select_related("group_details").get(
            pk=pk, kind=KIND_GROUP
        )
    except catalog_entity_model.DoesNotExist:
        raise _not_found("Group not found") from None


def _get_actor(pk) -> CatalogEntity:
    catalog_entity_model = get_catalog_entity_model()
    try:
        return catalog_entity_model.objects.select_related("actor_details").get(
            pk=pk, kind=KIND_ACTOR
        )
    except catalog_entity_model.DoesNotExist:
        raise _not_found("User not found") from None


class GroupDetailController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> GroupOut:
        return _group_out(_get_group(parsed_path.id))


class GroupRelationsController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> list[RelationOut]:
        return relations_out(_get_group(parsed_path.id))


class ActorListController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_query: Query[ListFilters]) -> list[ActorOut]:
        queryset = (
            get_catalog_entity_model()
            .objects.filter(kind=KIND_ACTOR)
            .select_related("actor_details")
        )
        queryset = filter_by_search(queryset, parsed_query.q)
        return [_actor_out(instance) for instance in queryset]


class ActorDetailController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> ActorOut:
        return _actor_out(_get_actor(parsed_path.id))


class ActorRelationsController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> list[RelationOut]:
        return relations_out(_get_actor(parsed_path.id))
