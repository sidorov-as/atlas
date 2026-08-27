"""Flow CRUD controllers — split out of
`server.apps.catalog.api.views`.

Flow isn't a `CatalogEntity` — writes
go straight through the ORM, not the core `EntityService`. Create, update,
and delete all require the `atlas.flows.flow.edit` permission, checked
against the Flow's `system` as the resource; list/retrieve require only `SessionAuth`.
"""

from http import HTTPStatus

from atlas_plugin_api import (
    FORBIDDEN_RESPONSE,
    KIND_SYSTEM,
    PageOut,
    PaginatedOut,
    SessionAuth,
    filter_by_search,
    filter_by_system,
    filter_by_team,
    resolve_ref,
)
from atlas_plugin_api.controllers import AtlasController
from django.core.paginator import Paginator
from dmr import Body, Path, Query, modify
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from ..models import Flow, resolve_step_ref_statuses
from ..permissions import check_flow_write_permission
from .schemas import FlowIn, FlowListFilters, FlowOut, FlowPatch, FlowPath


def _flow_out(instance: Flow) -> FlowOut:
    return FlowOut(
        id=instance.id,
        system=instance.system.ref,
        name=instance.name,
        description=instance.description,
        documentation=instance.documentation,
        steps=instance.steps,
        autolayout_enabled=instance.autolayout_enabled,
        layout_direction=instance.layout_direction,
        layout_engine=instance.layout_engine,
        ref_status=resolve_step_ref_statuses(instance.steps),
    )


def _get_flow(pk: int) -> Flow:
    try:
        return Flow.objects.select_related("system", "system__owner").get(pk=pk)
    except Flow.DoesNotExist:
        raise APIError(
            format_error("Flow not found", error_type=ErrorType.not_found),
            status_code=HTTPStatus.NOT_FOUND,
        ) from None


def _flow_create(body: FlowIn) -> Flow:
    instance = Flow()
    instance.system = resolve_ref(body.system, expected_kind=KIND_SYSTEM)
    instance.name = body.name
    instance.description = body.description
    instance.documentation = body.documentation
    instance.steps = body.steps
    instance.autolayout_enabled = body.autolayout_enabled
    instance.layout_direction = body.layout_direction
    instance.layout_engine = body.layout_engine
    return instance


def _apply_flow_patch(instance: Flow, body: FlowPatch) -> None:
    fields = body.model_fields_set
    if "system" in fields:
        instance.system = resolve_ref(body.system, expected_kind=KIND_SYSTEM)
    if "name" in fields:
        instance.name = body.name
    if "description" in fields:
        instance.description = body.description
    if "documentation" in fields:
        instance.documentation = body.documentation
    if "steps" in fields:
        instance.steps = body.steps
    if "autolayout_enabled" in fields:
        instance.autolayout_enabled = body.autolayout_enabled
    if "layout_direction" in fields:
        instance.layout_direction = body.layout_direction
    if "layout_engine" in fields:
        instance.layout_engine = body.layout_engine


class FlowListController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_query: Query[FlowListFilters]) -> PaginatedOut[FlowOut]:
        queryset = Flow.objects.select_related("system", "system__owner")
        queryset = filter_by_system(queryset, parsed_query.system)
        queryset = filter_by_team(queryset, parsed_query.team)
        queryset = filter_by_search(queryset, parsed_query.q)
        page = Paginator(
            queryset.order_by(parsed_query.sort, "id"), parsed_query.page_size
        ).page(parsed_query.page)
        return PaginatedOut(
            count=page.paginator.count,
            num_pages=page.paginator.num_pages,
            per_page=page.paginator.per_page,
            page=PageOut(
                number=page.number,
                object_list=[_flow_out(instance) for instance in page.object_list],
            ),
        )

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_body: Body[FlowIn]) -> FlowOut:
        instance = _flow_create(parsed_body)
        check_flow_write_permission(self.request.user, instance.system)
        instance.save()
        return _flow_out(instance)


class FlowDetailController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[FlowPath]) -> FlowOut:
        return _flow_out(_get_flow(parsed_path.id))

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def patch(
        self,
        parsed_path: Path[FlowPath],
        parsed_body: Body[FlowPatch],
    ) -> FlowOut:
        instance = _get_flow(parsed_path.id)
        check_flow_write_permission(self.request.user, instance.system)
        _apply_flow_patch(instance, parsed_body)
        instance.save()
        return _flow_out(instance)

    @modify(status_code=HTTPStatus.NO_CONTENT, extra_responses=[FORBIDDEN_RESPONSE])
    def delete(self, parsed_path: Path[FlowPath]) -> None:
        instance = _get_flow(parsed_path.id)
        check_flow_write_permission(self.request.user, instance.system)
        instance.delete()
