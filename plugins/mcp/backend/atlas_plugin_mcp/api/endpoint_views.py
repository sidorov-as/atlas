"""API Endpoint/Operation controllers for the MCP API: `search_api_endpoints`,
`get_api_endpoint`, `get_endpoint_consumers`, `search_api_operations`,
`get_api_operation`, `get_operation_consumers` (`mcp-plugin` spec's "API
Endpoint/Operation tools are present only when atlas.apis is installed").

Only ever imported by `atlas_plugin_mcp.api.urls` after that module has
already confirmed `atlas_plugin_apis` is installed — importing it
unconditionally would crash a distribution that selects `atlas.mcp` without
`atlas.apis`.

Calls only `atlas_plugin_apis.extension_points`, never its models or REST
controllers: each function there enforces the same read/dependency-read
permission its REST counterpart does, against the PAT's owning user. Like
every existing MCP read tool, these need a valid PAT but no particular scope.
"""

from http import HTTPStatus

from atlas_plugin_api import FORBIDDEN_RESPONSE, PageOut, PaginatedOut, PATBearerAuth
from atlas_plugin_api.controllers import AtlasController
from atlas_plugin_apis import extension_points
from dmr import Path, Query, modify
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from .schemas import (
    ApiEndpointSearchQuery,
    ApiOperationSearchQuery,
    ConsumerServiceOut,
    EndpointConsumersOut,
    EndpointOut,
    EndpointPath,
    EndpointSummaryOut,
    OperationConsumerOut,
    OperationConsumersOut,
    OperationOut,
    OperationPath,
    OperationSummaryOut,
)


def _not_found(what: str) -> APIError:
    return APIError(
        format_error(f"{what} not found", error_type=ErrorType.not_found),
        status_code=HTTPStatus.NOT_FOUND,
    )


def _service_out(service) -> ConsumerServiceOut:
    return ConsumerServiceOut(
        id=service.id,
        ref=service.ref,
        name=service.name,
        title=service.title,
        team=service.owner.ref if service.owner else None,
    )


def _endpoint_summary(instance) -> EndpointSummaryOut:
    return EndpointSummaryOut(
        id=instance.id,
        api=instance.api.ref,
        api_id=instance.api_id,
        method=instance.method,
        path=instance.path,
        summary=instance.summary,
        deprecated=instance.deprecated,
        status=instance.status,
    )


def _endpoint_out(instance) -> EndpointOut:
    return EndpointOut(
        **_endpoint_summary(instance).model_dump(),
        operation_id=instance.operation_id,
        description=instance.description,
        tags=instance.tags,
        request=instance.request or {},
        responses=instance.responses or [],
        security=instance.security or [],
        external_docs=instance.external_docs or None,
    )


def _operation_summary(instance) -> OperationSummaryOut:
    return OperationSummaryOut(
        id=instance.id,
        api=instance.api.ref,
        api_id=instance.api_id,
        channel_address=instance.channel_address,
        channel_protocol=instance.channel_protocol,
        direction=instance.direction,
        summary=instance.summary,
        deprecated=instance.deprecated,
        status=instance.status,
    )


def _operation_out(instance) -> OperationOut:
    return OperationOut(
        **_operation_summary(instance).model_dump(),
        operation_key=instance.operation_key,
        operation_id=instance.operation_id,
        description=instance.description,
        tags=instance.tags,
        messages=instance.message or [],
        external_docs=instance.external_docs or None,
        delivery=instance.delivery or {},
    )


def _paginated(page, convert) -> PaginatedOut:
    return PaginatedOut(
        count=page.paginator.count,
        num_pages=page.paginator.num_pages,
        per_page=page.paginator.per_page,
        page=PageOut(
            number=page.number,
            object_list=[convert(instance) for instance in page.object_list],
        ),
    )


class EndpointSearchController(AtlasController):
    """The `search_api_endpoints` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="search_api_endpoints",
        summary="Search API endpoints",
        description=(
            "Search active HTTP (OpenAPI) Endpoints by free-text `q` matched "
            "against path, summary, and operation id — across every API, or "
            "only one API's when `apiId` is given. Returns each Endpoint's "
            "id, owning API, method, path, and summary only — call "
            "`get_api_endpoint` for its request/response shapes, and "
            "`get_endpoint_consumers` for which Services use it."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def get(
        self, parsed_query: Query[ApiEndpointSearchQuery]
    ) -> PaginatedOut[EndpointSummaryOut]:
        page = extension_points.search_endpoints(
            self.request.user,
            query=parsed_query.q,
            api_id=parsed_query.api_id,
            page=parsed_query.page,
            page_size=parsed_query.page_size,
        )
        return _paginated(page, _endpoint_summary)


class EndpointDetailController(AtlasController):
    """The `get_api_endpoint` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="get_api_endpoint",
        summary="Get an API endpoint",
        description=(
            "Read one HTTP Endpoint by id: method, path, request parameters "
            "and body, responses, security, deprecation, and `status` "
            "(`removed` Endpoints still resolve — check it)."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def get(self, parsed_path: Path[EndpointPath]) -> EndpointOut:
        instance = extension_points.get_endpoint(self.request.user, parsed_path.id)
        if instance is None:
            raise _not_found("Endpoint")
        return _endpoint_out(instance)


class EndpointConsumersController(AtlasController):
    """The `get_endpoint_consumers` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="get_endpoint_consumers",
        summary="Get an API endpoint's consuming services",
        description=(
            "The Services explicitly linked as consumers of one Endpoint "
            '(by id). Use this to answer "which services use this '
            'endpoint" — it is finer-grained than an API-wide `consumesApi` '
            "relation, which only says a Service uses the API as a whole."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def get(self, parsed_path: Path[EndpointPath]) -> EndpointConsumersOut:
        services = extension_points.get_endpoint_consumers(
            self.request.user, parsed_path.id
        )
        endpoint = extension_points.resolve_endpoint(parsed_path.id)
        if services is None or endpoint is None:
            raise _not_found("Endpoint")
        return EndpointConsumersOut(
            endpoint=_endpoint_summary(endpoint),
            services=[_service_out(service) for service in services],
        )


class OperationSearchController(AtlasController):
    """The `search_api_operations` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="search_api_operations",
        summary="Search API operations",
        description=(
            "Search active AsyncAPI Operations by free-text `q` matched "
            "against channel address, summary, and operation id — across "
            "every API, or only one API's when `apiId` is given. Returns "
            "each Operation's id, owning API, channel, and direction only — "
            "call `get_api_operation` for its messages, and "
            "`get_operation_consumers` for which Services publish/subscribe."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def get(
        self, parsed_query: Query[ApiOperationSearchQuery]
    ) -> PaginatedOut[OperationSummaryOut]:
        page = extension_points.search_operations(
            self.request.user,
            query=parsed_query.q,
            api_id=parsed_query.api_id,
            page=parsed_query.page,
            page_size=parsed_query.page_size,
        )
        return _paginated(page, _operation_summary)


class OperationDetailController(AtlasController):
    """The `get_api_operation` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="get_api_operation",
        summary="Get an API operation",
        description=(
            "Read one AsyncAPI Operation by id: channel, direction, "
            "messages, deprecation, and `status` (`removed` Operations "
            "still resolve — check it)."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def get(self, parsed_path: Path[OperationPath]) -> OperationOut:
        instance = extension_points.get_operation(self.request.user, parsed_path.id)
        if instance is None:
            raise _not_found("Operation")
        return _operation_out(instance)


class OperationConsumersController(AtlasController):
    """The `get_operation_consumers` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="get_operation_consumers",
        summary="Get an API operation's publishing and subscribing services",
        description=(
            "The Services that publish or subscribe on one Operation's "
            "channel (by id), each with its `role`. Use this to answer "
            '"which services use this operation" — it is finer-grained '
            "than an API-wide `consumesApi` relation."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def get(self, parsed_path: Path[OperationPath]) -> OperationConsumersOut:
        participants = extension_points.get_operation_consumers(
            self.request.user, parsed_path.id
        )
        operation = extension_points.resolve_operation(parsed_path.id)
        if participants is None or operation is None:
            raise _not_found("Operation")
        return OperationConsumersOut(
            operation=_operation_summary(operation),
            participants=[
                OperationConsumerOut(service=_service_out(service), role=role)
                for service, role in participants
            ],
        )
