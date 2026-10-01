"""Flow CRUD controllers — split out of
`server.apps.catalog.api.views`.

Flow isn't a `CatalogEntity` — list/get/create/update/delete all go through
the published `FlowService` contract (`extension_points.get_flow_service()`)
rather than the ORM/permission helpers directly, so this module never
diverges from what `atlas.mcp` (or any other future caller) gets through
the same contract. Create, update, and delete all require the
`atlas.flows.flow.edit` permission, checked by `FlowService` against the
Flow's `system` as the resource; list/retrieve require only `SessionAuth`.
"""

from http import HTTPStatus
from typing import Any

from atlas_plugin_api import (
    FORBIDDEN_RESPONSE,
    PageOut,
    PaginatedOut,
    SessionAuth,
)
from atlas_plugin_api.controllers import AtlasController
from django.core.paginator import Paginator
from dmr import Body, Path, Query, modify
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from ..contracts import FlowNotFoundError
from ..extension_points import get_flow_service
from ..models import Flow, resolve_step_ref_statuses
from ..permissions import can_edit_flow
from .schemas import (
    FlowIn,
    FlowListFilters,
    FlowOut,
    FlowPatch,
    FlowPath,
    FlowPermissionsOut,
)


def _flow_out(instance: Flow, user: Any = None) -> FlowOut:
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
        permissions=(
            FlowPermissionsOut(can_edit=can_edit_flow(user, instance.system))
            if user
            else None
        ),
    )


def _not_found() -> APIError:
    return APIError(
        format_error("Flow not found", error_type=ErrorType.not_found),
        status_code=HTTPStatus.NOT_FOUND,
    )


class FlowListController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_query: Query[FlowListFilters]) -> PaginatedOut[FlowOut]:
        queryset = get_flow_service().list(
            system=parsed_query.system,
            team=parsed_query.team,
            search=parsed_query.q,
        )
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
        instance = get_flow_service().create(body=parsed_body, actor=self.request.user)
        return _flow_out(instance, self.request.user)


class FlowDetailController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[FlowPath]) -> FlowOut:
        try:
            instance = get_flow_service().get(parsed_path.id)
        except FlowNotFoundError:
            raise _not_found() from None
        return _flow_out(instance, self.request.user)

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def patch(
        self,
        parsed_path: Path[FlowPath],
        parsed_body: Body[FlowPatch],
    ) -> FlowOut:
        try:
            instance = get_flow_service().update(
                flow_id=parsed_path.id, body=parsed_body, actor=self.request.user
            )
        except FlowNotFoundError:
            raise _not_found() from None
        return _flow_out(instance, self.request.user)

    @modify(status_code=HTTPStatus.NO_CONTENT, extra_responses=[FORBIDDEN_RESPONSE])
    def delete(self, parsed_path: Path[FlowPath]) -> None:
        try:
            get_flow_service().delete(flow_id=parsed_path.id, actor=self.request.user)
        except FlowNotFoundError:
            raise _not_found() from None
