"""Usage link controllers for the MCP API: `link_endpoint_consumers`,
`unlink_endpoint_consumers`, `link_operation_participants`,
`unlink_operation_participants` (`mcp-api-usage-tools` spec).

Only ever imported by `atlas_plugin_mcp.api.urls` after that module has
already confirmed `atlas_plugin_apis` is installed — importing it
unconditionally would crash a distribution that selects `atlas.mcp` without
`atlas.apis`.

Each tool takes one Service and a batch of items, checks the `apis:write`
scope first, and then calls only `atlas_plugin_apis.extension_points` — the
same link rules the SPA's REST controllers use — with `source="mcp"`. It
imports no apis model or REST controller.
"""

from http import HTTPStatus

from atlas_plugin_api import (
    FORBIDDEN_RESPONSE,
    KIND_COMPONENT,
    PATBearerAuth,
    require_scope,
)
from atlas_plugin_api.controllers import AtlasController
from atlas_plugin_api.refs import RefError, parse_ref, resolve_ref
from atlas_plugin_apis import extension_points
from dmr import Body, Query, ResponseSpec, modify
from dmr.errors import ErrorModel, ErrorType, format_error
from dmr.response import APIError

from .schemas import (
    DryRunQuery,
    EndpointUsageItemIn,
    LinkEndpointConsumersIn,
    LinkOperationParticipantsIn,
    OperationUsageItemIn,
    UsageItemOut,
    UsageLinksOut,
)

_SCOPE_APIS_WRITE = "apis:write"

_SERVICE_NOT_FOUND_RESPONSE = ResponseSpec(
    ErrorModel,
    status_code=HTTPStatus.NOT_FOUND,
    description="The Service ref does not resolve",
)

_BATCH_NOTE = (
    f"Takes one Service and up to {extension_points.MAX_USAGE_BATCH_SIZE} items; "
    "every item is applied on its own and gets its own `status`, so one bad item "
    "does not fail the rest, and sending the same batch again is safe. Name each "
    "target by id, or by its natural key. With `dryRun` true nothing is saved and "
    "the statuses preview the real call. Requires the `apis:write` PAT scope and "
    "the same permission on the Service as the web UI."
)


def _bad_request(message: str) -> APIError:
    return APIError(
        format_error(message, error_type=ErrorType.value_error),
        status_code=HTTPStatus.BAD_REQUEST,
    )


def _resolve_service(ref: str):
    """The Component `ref` names; 400 for a malformed ref or another kind, 404 if none."""
    try:
        kind, _namespace, _name = parse_ref(ref, default_kind=KIND_COMPONENT)
    except RefError as exc:
        raise _bad_request(str(exc)) from None
    if kind != KIND_COMPONENT:
        raise _bad_request(
            f"{ref!r} is a {kind}; only a Component (Service) can be linked"
        )
    try:
        return resolve_ref(ref, expected_kind=KIND_COMPONENT)
    except RefError as exc:
        raise APIError(
            format_error(str(exc), error_type=ErrorType.not_found),
            status_code=HTTPStatus.NOT_FOUND,
        ) from None


def _endpoint_items(
    items: list[EndpointUsageItemIn],
) -> list[extension_points.UsageItem]:
    return [
        extension_points.UsageItem(
            endpoint_id=item.endpoint_id,
            api=item.api,
            method=item.method,
            path=item.path,
        )
        for item in items
    ]


def _operation_items(
    items: list[OperationUsageItemIn],
) -> list[extension_points.UsageItem]:
    return [
        extension_points.UsageItem(
            operation_id=item.operation_id,
            api=item.api,
            channel_address=item.channel_address,
            direction=item.direction,
            role=item.role,
        )
        for item in items
    ]


def _out(result: extension_points.UsageBatchResult) -> UsageLinksOut:
    return UsageLinksOut(
        items=[
            UsageItemOut(
                status=item.status,
                message=item.message,
                endpoint_id=item.endpoint_id,
                operation_id=item.operation_id,
                candidates=item.candidates,
                api_relation_created=item.api_relation_created,
            )
            for item in result.items
        ],
        counts=result.counts,
        dry_run=result.dry_run,
        warnings=result.warnings,
    )


class LinkEndpointConsumersController(AtlasController):
    """The `link_endpoint_consumers` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="link_endpoint_consumers",
        summary="Link a service to API endpoints it consumes",
        description=(
            "Record that a Service (Component) consumes HTTP (OpenAPI) Endpoints. "
            "Each item is `{endpointId}` or `{api, method, path}`. An item for a "
            "removed Endpoint is a `conflict`. Linking also adds the Endpoint's API "
            "to the Service's `consumesAPI` when it is not there yet, reported per "
            "item as `apiRelationCreated`. " + _BATCH_NOTE
        ),
        status_code=HTTPStatus.OK,
        extra_responses=[FORBIDDEN_RESPONSE, _SERVICE_NOT_FOUND_RESPONSE],
    )
    def post(
        self,
        parsed_body: Body[LinkEndpointConsumersIn],
        parsed_query: Query[DryRunQuery],
    ) -> UsageLinksOut:
        require_scope(self, _SCOPE_APIS_WRITE)
        service = _resolve_service(parsed_body.service)
        return _out(
            extension_points.link_endpoints(
                self.request.user,
                service,
                _endpoint_items(parsed_body.items),
                source="mcp",
                dry=parsed_query.dry_run,
            )
        )


class UnlinkEndpointConsumersController(AtlasController):
    """The `unlink_endpoint_consumers` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="unlink_endpoint_consumers",
        summary="Unlink a service from API endpoints",
        description=(
            "Remove a Service's links to HTTP (OpenAPI) Endpoints. Each item is "
            "`{endpointId}` or `{api, method, path}`; a removed Endpoint can still "
            "be unlinked. An item with no such link is `unchanged`. A link managed "
            "by ingestion is a `conflict` and stays. The Service's `consumesAPI` is "
            "never removed. " + _BATCH_NOTE
        ),
        status_code=HTTPStatus.OK,
        extra_responses=[FORBIDDEN_RESPONSE, _SERVICE_NOT_FOUND_RESPONSE],
    )
    def post(
        self,
        parsed_body: Body[LinkEndpointConsumersIn],
        parsed_query: Query[DryRunQuery],
    ) -> UsageLinksOut:
        require_scope(self, _SCOPE_APIS_WRITE)
        service = _resolve_service(parsed_body.service)
        return _out(
            extension_points.unlink_endpoints(
                self.request.user,
                service,
                _endpoint_items(parsed_body.items),
                dry=parsed_query.dry_run,
            )
        )


class LinkOperationParticipantsController(AtlasController):
    """The `link_operation_participants` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="link_operation_participants",
        summary="Link a service to API operations it publishes or subscribes to",
        description=(
            "Record that a Service (Component) publishes or subscribes on AsyncAPI "
            "Operations. Each item is `{operationId, role}` or `{api, "
            "channelAddress, direction, role}`; `role` is `publisher` or "
            "`subscriber`, and one Service may hold both on an Operation. A key "
            "matching several active Operations is `ambiguous`; retry with one of "
            "the returned ids. The Operation's own document owner is a `conflict`. "
            "The Service's relations are not changed. " + _BATCH_NOTE
        ),
        status_code=HTTPStatus.OK,
        extra_responses=[FORBIDDEN_RESPONSE, _SERVICE_NOT_FOUND_RESPONSE],
    )
    def post(
        self,
        parsed_body: Body[LinkOperationParticipantsIn],
        parsed_query: Query[DryRunQuery],
    ) -> UsageLinksOut:
        require_scope(self, _SCOPE_APIS_WRITE)
        service = _resolve_service(parsed_body.service)
        return _out(
            extension_points.link_operations(
                self.request.user,
                service,
                _operation_items(parsed_body.items),
                source="mcp",
                dry=parsed_query.dry_run,
            )
        )


class UnlinkOperationParticipantsController(AtlasController):
    """The `unlink_operation_participants` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="unlink_operation_participants",
        summary="Unlink a service from API operations",
        description=(
            "Remove a Service's role on AsyncAPI Operations. Each item is "
            "`{operationId, role}` or `{api, channelAddress, direction, role}`; "
            "only that role is removed, the Service's other role stays. An item "
            "with no such link is `unchanged`. A link managed by ingestion is a "
            "`conflict` and stays. " + _BATCH_NOTE
        ),
        status_code=HTTPStatus.OK,
        extra_responses=[FORBIDDEN_RESPONSE, _SERVICE_NOT_FOUND_RESPONSE],
    )
    def post(
        self,
        parsed_body: Body[LinkOperationParticipantsIn],
        parsed_query: Query[DryRunQuery],
    ) -> UsageLinksOut:
        require_scope(self, _SCOPE_APIS_WRITE)
        service = _resolve_service(parsed_body.service)
        return _out(
            extension_points.unlink_operations(
                self.request.user,
                service,
                _operation_items(parsed_body.items),
                dry=parsed_query.dry_run,
            )
        )
