"""Flow controllers for the MCP API: `list_flows`, `get_flow`,
`create_flow`, `update_flow`, `delete_flow` (`mcp-plugin` spec's "Flow tools
are present only when atlas.flows is installed").

Only ever imported by `atlas_plugin_mcp.api.urls` after that module has
already confirmed `atlas_plugin_flows` is installed
(`django.apps.apps.is_installed`) — importing it unconditionally would
crash a distribution that selects `atlas.mcp` without `atlas.flows`.

Routes through the published `FlowService` contract
(`atlas_plugin_flows.extension_points.get_flow_service`), never Flow's own
REST controllers or ORM directly, so a Flow operation here can never
diverge from what the existing Flow REST API does (`flows-plugin` spec:
"Flow writes route through FlowService"). Write bodies reuse
`atlas_plugin_flows.contracts.FlowIn`/`FlowPatch` directly rather than
redefining an equivalent MCP-local schema: unlike catalog's per-kind
`spec` (genuinely different shape per kind, with no single fixed body this
module could declare), Flow has exactly one shape, already published by
`atlas_plugin_flows.contracts` specifically "for other plugins (notably the
new `atlas.mcp`)" to depend on (that module's own docstring) — redefining
it here would only risk its field-level validators (ref/name syntax, step
shape) drifting from the one `FlowService`/the REST controllers actually
enforce.

Writes require the `flows:write` PAT scope in addition to a valid token
(`atlas_plugin_api.require_scope`), matching `views.py`'s catalog-write
scope gate and the `mcp-plugin` spec's "PAT scopes narrow the MCP API's
effective permissions".
"""

from http import HTTPStatus

from atlas_plugin_api import (
    FORBIDDEN_RESPONSE,
    PageOut,
    PaginatedOut,
    PATBearerAuth,
    require_scope,
)
from atlas_plugin_api.controllers import AtlasController
from atlas_plugin_flows.contracts import FlowIn, FlowNotFoundError, FlowPatch
from atlas_plugin_flows.extension_points import get_flow_service
from django.core.paginator import Paginator
from dmr import Body, Path, Query, modify
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from .schemas import FlowListQuery, FlowOut, FlowPath, FlowSummaryOut

_SCOPE_FLOWS_WRITE = "flows:write"


def _not_found() -> APIError:
    return APIError(
        format_error("Flow not found", error_type=ErrorType.not_found),
        status_code=HTTPStatus.NOT_FOUND,
    )


def _summary_out(instance) -> FlowSummaryOut:
    return FlowSummaryOut(
        id=instance.id,
        system=instance.system.ref,
        name=instance.name,
        description=instance.description,
    )


def _flow_out(instance) -> FlowOut:
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
    )


class FlowListController(AtlasController):
    """The `list_flows` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="list_flows",
        summary="List flows",
        description=(
            "Search Flows across every System, optionally filtered by "
            "`system`, `team`, or a free-text query. Returns each Flow's "
            "id, system, name, and description only — call `get_flow` for a "
            "given id to read its full step graph and documentation."
        ),
    )
    def get(self, parsed_query: Query[FlowListQuery]) -> PaginatedOut[FlowSummaryOut]:
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
                object_list=[_summary_out(instance) for instance in page.object_list],
            ),
        )

    @modify(
        operation_id="create_flow",
        summary="Create a flow",
        description=(
            "Create a new Flow: a named, documented step graph (e.g. "
            "components, resources, and terminal outcomes) attached to a "
            "System. A step's `icon` is a `@gravity-ui/icons` component "
            "name — use `search_flow_icons` to find a valid one before "
            "setting it. Requires the `flows:write` PAT scope."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def post(self, parsed_body: Body[FlowIn]) -> FlowOut:
        require_scope(self, _SCOPE_FLOWS_WRITE)
        instance = get_flow_service().create(body=parsed_body, actor=self.request.user)
        return _flow_out(instance)


class FlowDetailController(AtlasController):
    """The `get_flow` (GET), `update_flow` (PATCH), and `delete_flow`
    (DELETE) MCP tools."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="get_flow",
        summary="Get a flow",
        description=(
            "Read one Flow by id: its full step graph, documentation, and "
            "layout settings."
        ),
    )
    def get(self, parsed_path: Path[FlowPath]) -> FlowOut:
        try:
            instance = get_flow_service().get(parsed_path.id)
        except FlowNotFoundError:
            raise _not_found() from None
        return _flow_out(instance)

    @modify(
        operation_id="update_flow",
        summary="Update a flow",
        description=(
            "Partially update a Flow by id — an omitted field is left "
            "untouched. Requires the `flows:write` PAT scope."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def patch(
        self,
        parsed_path: Path[FlowPath],
        parsed_body: Body[FlowPatch],
    ) -> FlowOut:
        require_scope(self, _SCOPE_FLOWS_WRITE)
        try:
            instance = get_flow_service().update(
                flow_id=parsed_path.id, body=parsed_body, actor=self.request.user
            )
        except FlowNotFoundError:
            raise _not_found() from None
        return _flow_out(instance)

    @modify(
        operation_id="delete_flow",
        summary="Delete a flow",
        description="Permanently delete a Flow by id. Requires the `flows:write` PAT scope.",
        status_code=HTTPStatus.NO_CONTENT,
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def delete(self, parsed_path: Path[FlowPath]) -> None:
        require_scope(self, _SCOPE_FLOWS_WRITE)
        try:
            get_flow_service().delete(flow_id=parsed_path.id, actor=self.request.user)
        except FlowNotFoundError:
            raise _not_found() from None
