"""Entity CRUD controllers for the API kind —
split out of `server.apps.catalog.api.views`.

Every entity is one `CatalogEntity` row joined to its kind-specific
`ApiDetails` row. API writes
(create/update/delete) go exclusively through the core `EntityService`
via the registered `ApiKindHandler` — this
module owns request parsing, response shaping, and the `_get_api` 404/kind
guard, not persistence.
"""

from http import HTTPStatus

from atlas_plugin_api import (
    API_VERSION,
    FORBIDDEN_RESPONSE,
    KIND_API,
    KIND_COMPONENT,
    STATUS_ACTIVE,
    AdoptIn,
    CatalogEntity,
    EntityPath,
    HistoryRecordOut,
    ListFilters,
    PageOut,
    PaginatedOut,
    RelationOut,
    SessionAuth,
    adopt,
    blocked_by,
    blocked_by_reason,
    delete_blocked,
    entity_capabilities,
    entity_relations,
    filter_by_field,
    filter_by_owner,
    filter_by_search,
    filter_by_status,
    filter_by_system,
    filter_by_tags_overlap,
    get_catalog_entity_model,
    get_entity_service,
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
from atlas_plugin_standard_catalog.extension_points import add_consumed_api
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from dmr import Body, Path, Query, ResponseSpec, modify
from dmr.errors import ErrorModel, ErrorType, format_error
from dmr.response import APIError

from ..models import (
    ApiEndpoint,
    ApiOperation,
    ServiceEndpointUsage,
    ServiceOperationUsage,
)
from ..permissions import (
    check_endpoint_dependency_create_permission,
    check_endpoint_dependency_delete_permission,
    check_endpoint_dependency_read_permission,
    check_endpoint_purge_permission,
    check_endpoint_read_permission,
    check_operation_dependency_create_permission,
    check_operation_dependency_delete_permission,
    check_operation_dependency_read_permission,
    check_operation_purge_permission,
    check_operation_read_permission,
)
from .schemas import (
    ApiEndpointListQuery,
    ApiEndpointPath,
    ApiEndpointSearchQuery,
    ApiEndpointsPath,
    ApiIn,
    ApiOperationListQuery,
    ApiOperationPath,
    ApiOperationSearchQuery,
    ApiOperationsPath,
    ApiOut,
    ApiPatch,
    ApiSpecOut,
    ApiSummaryOut,
    EndpointConsumersOut,
    EndpointConsumerSummaryOut,
    EndpointOut,
    EndpointRequestOut,
    EndpointResponseOut,
    EndpointSearchResultOut,
    EndpointSecurityOut,
    EndpointServiceLinkIn,
    EndpointServiceLinkOut,
    EndpointServiceOut,
    EndpointServicePath,
    EndpointServicesPath,
    EndpointServicesQuery,
    ExternalDocsOut,
    OperationConsumerParticipantOut,
    OperationConsumersOut,
    OperationConsumerSummaryOut,
    OperationMessageOut,
    OperationOut,
    OperationProviderOut,
    OperationSearchResultOut,
    OperationServiceDeleteQuery,
    OperationServiceLinkIn,
    OperationServiceLinkOut,
    OperationServiceOut,
    OperationServicePath,
    OperationServicesPath,
    OperationServicesQuery,
    ServiceSummaryOut,
)


def _api_out(instance: CatalogEntity) -> ApiOut:
    details = instance.api_details
    return ApiOut(
        id=instance.id,
        api_version=API_VERSION,
        metadata=metadata_out(instance),
        spec=ApiSpecOut(
            type=details.type,
            owner=instance.owner.ref,
            owner_id=instance.owner.id,
            system=details.system.ref,
            system_id=details.system.id,
            spec_source=details.spec_source,
            spec_url=details.spec_url,
            spec_content=details.spec_content,
            spec_resolved_at=details.spec_resolved_at,
            spec_resolve_failed=details.spec_resolve_failed,
            endpoints_synced_at=details.endpoints_synced_at,
            endpoints_sync_failed=details.endpoints_sync_failed,
            operations_synced_at=details.operations_synced_at,
            operations_sync_failed=details.operations_sync_failed,
            resolved_base_url=details.resolved_base_url,
            resolved_protocol=details.resolved_protocol,
        ),
        status=instance.status,
        ingested_from=ingested_from(instance),
        blocked_by=blocked_by(instance),
        blocked_by_reason=blocked_by_reason(instance),
        capabilities=entity_capabilities(instance),
    )


def _get_api(pk) -> CatalogEntity:
    catalog_entity_model = get_catalog_entity_model()
    try:
        return catalog_entity_model.objects.select_related(
            "owner",
            "ingested_from",
            "api_details",
            "api_details__system",
        ).get(pk=pk, kind=KIND_API)
    except catalog_entity_model.DoesNotExist:
        raise APIError(
            format_error("API not found", error_type=ErrorType.not_found),
            status_code=HTTPStatus.NOT_FOUND,
        ) from None


class ApiListController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_query: Query[ListFilters]) -> PaginatedOut[ApiOut]:
        queryset = (
            get_catalog_entity_model()
            .objects.filter(kind=KIND_API)
            .select_related(
                "owner",
                "ingested_from",
                "api_details",
                "api_details__system",
            )
        )
        queryset = filter_by_owner(queryset, parsed_query.owner)
        queryset = filter_by_system(
            queryset, parsed_query.system, prefix="api_details__"
        )
        queryset = filter_by_field(
            queryset, "type", parsed_query.type, prefix="api_details__"
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
                object_list=[_api_out(instance) for instance in page.object_list],
            ),
        )

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_body: Body[ApiIn]) -> ApiOut:
        entity = get_entity_service().create(
            kind_id=KIND_API,
            owner_ref=parsed_body.spec.owner,
            metadata=parsed_body.metadata,
            spec=parsed_body.spec,
            actor=self.request.user,
        )
        return _api_out(entity)


class ApiDetailController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> ApiOut:
        return _api_out(_get_api(parsed_path.id))

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def patch(
        self,
        parsed_path: Path[EntityPath],
        parsed_body: Body[ApiPatch],
    ) -> ApiOut:
        _get_api(parsed_path.id)
        entity = get_entity_service().update(
            entity_id=parsed_path.id,
            owner_ref=spec_owner_ref(parsed_body.spec),
            metadata=parsed_body.metadata,
            spec=parsed_body.spec,
            actor=self.request.user,
        )
        return _api_out(entity)

    # No `delete`: retired in favor of Remove -> Purge as the sole destructive path (D14).


class ApiRelationsController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> list[RelationOut]:
        return relations_out(_get_api(parsed_path.id))


class ApiHistoryController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> list[HistoryRecordOut]:
        return history_out(_get_api(parsed_path.id))


class ApiAdoptController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.OK, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath], parsed_body: Body[AdoptIn]) -> ApiOut:
        instance = _get_api(parsed_path.id)
        adopt(instance, self.request, parsed_body)
        return _api_out(instance)


class ApiRemoveController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.OK, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath]) -> ApiOut:
        _get_api(parsed_path.id)
        entity = remove_entity(parsed_path.id, self.request.user)
        return _api_out(entity)


class ApiReviveController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.OK, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath]) -> ApiOut:
        _get_api(parsed_path.id)
        entity = revive_entity(parsed_path.id, self.request.user)
        return _api_out(entity)


class ApiPurgeController(AtlasController):
    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.NO_CONTENT, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[EntityPath]) -> None:
        _get_api(parsed_path.id)
        purge_entity(parsed_path.id, self.request.user)


# --- Endpoint -------------------------
#
# Read-only: only the two `GET` views
# below exist, each explicitly gated on `endpoint.read`
# (`check_endpoint_read_permission`) the same way
# `atlas_plugin_c4.api.views.DiagramController` gates on
# `atlas.c4.diagram.read` — `Endpoint` isn't a registered Entity Kind, so it
# gets none of the generic per-kind permission wiring `api` itself gets.


def _endpoint_out(instance: ApiEndpoint) -> EndpointOut:
    return EndpointOut(
        id=instance.id,
        api_id=instance.api_id,
        method=instance.method,
        path=instance.path,
        operation_id=instance.operation_id,
        summary=instance.summary,
        description=instance.description,
        deprecated=instance.deprecated,
        tags=instance.tags,
        request=EndpointRequestOut.model_validate(instance.request or {}),
        responses=[
            EndpointResponseOut.model_validate(response)
            for response in instance.responses
        ],
        external_docs=ExternalDocsOut.model_validate(instance.external_docs)
        if instance.external_docs
        else None,
        security=[
            EndpointSecurityOut.model_validate(entry) for entry in instance.security
        ],
        status=instance.status,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


def _get_endpoint(api: CatalogEntity, endpoint_id) -> ApiEndpoint:
    try:
        return ApiEndpoint.objects.get(pk=endpoint_id, api_id=api.id)
    except ApiEndpoint.DoesNotExist:
        raise APIError(
            format_error("Endpoint not found", error_type=ErrorType.not_found),
            status_code=HTTPStatus.NOT_FOUND,
        ) from None


class ApiEndpointListController(AtlasController):
    auth = (SessionAuth(),)

    def get(
        self,
        parsed_path: Path[ApiEndpointsPath],
        parsed_query: Query[ApiEndpointListQuery],
    ) -> list[EndpointOut]:
        check_endpoint_read_permission(self.request.user)
        api = _get_api(parsed_path.api_id)
        queryset = ApiEndpoint.objects.filter(api_id=api.id, status=parsed_query.status)
        if parsed_query.method:
            queryset = queryset.filter(method=parsed_query.method)
        if parsed_query.tag:
            queryset = queryset.filter(tags__contains=[parsed_query.tag])
        if parsed_query.deprecated is not None:
            queryset = queryset.filter(deprecated=parsed_query.deprecated)
        if parsed_query.search:
            queryset = queryset.filter(
                Q(path__icontains=parsed_query.search)
                | Q(summary__icontains=parsed_query.search)
                | Q(operation_id__icontains=parsed_query.search),
            )
        return [_endpoint_out(instance) for instance in queryset]


class ApiEndpointDetailController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[ApiEndpointPath]) -> EndpointOut:
        check_endpoint_read_permission(self.request.user)
        api = _get_api(parsed_path.api_id)
        return _endpoint_out(_get_endpoint(api, parsed_path.id))


class ApiEndpointPurgeController(AtlasController):
    """Purge a removed Endpoint
    — the one write action `Endpoint` gets, alongside its
    otherwise read-only surface. Gated
    the same way whole-entity Purge is (`check_endpoint_purge_permission`,
    scoped to the owning `api`'s owner Group), not `check_endpoint_read_
    permission`."""

    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.NO_CONTENT, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[ApiEndpointPath]) -> None:
        api = _get_api(parsed_path.api_id)
        endpoint = _get_endpoint(api, parsed_path.id)
        check_endpoint_purge_permission(self.request.user, api)
        if endpoint.status != ApiEndpoint.STATUS_REMOVED:
            raise delete_blocked(
                "Cannot purge this Endpoint: only a removed Endpoint may be purged"
            )
        blocking = [
            f"Service {usage.service.name!r}"
            for usage in ServiceEndpointUsage.objects.filter(
                endpoint=endpoint
            ).select_related("service")
            if usage.service.status == STATUS_ACTIVE
        ]
        if blocking:
            raise delete_blocked(
                f"Cannot purge this Endpoint: still referenced by {', '.join(blocking)}"
            )
        with transaction.atomic():
            # `ServiceEndpointUsage.endpoint`'s `on_delete=CASCADE` cleans up
            # every remaining (already-removed-Service-only, per the check
            # above) link automatically — no separate cascade step needed.
            endpoint.delete()


def _api_summary_out(api: CatalogEntity) -> ApiSummaryOut:
    return ApiSummaryOut(ref=api.ref, name=api.name, title=api.title)


class ApiEndpointSearchController(AtlasController):
    """Cross-API Endpoint search — a flat lookup across every API's active endpoints,
    backing the Flow "Add Step" Query picker, unlike
    `ApiEndpointListController`'s per-API list above."""

    auth = (SessionAuth(),)

    def get(
        self, parsed_query: Query[ApiEndpointSearchQuery]
    ) -> PaginatedOut[EndpointSearchResultOut]:
        check_endpoint_read_permission(self.request.user)
        queryset = ApiEndpoint.objects.filter(
            status=ApiEndpoint.STATUS_ACTIVE
        ).select_related("api")
        if parsed_query.search:
            queryset = queryset.filter(
                Q(path__icontains=parsed_query.search)
                | Q(summary__icontains=parsed_query.search)
                | Q(operation_id__icontains=parsed_query.search),
            )
        page = Paginator(queryset, parsed_query.page_size).page(parsed_query.page)
        return PaginatedOut(
            count=page.paginator.count,
            num_pages=page.paginator.num_pages,
            per_page=page.paginator.per_page,
            page=PageOut(
                number=page.number,
                object_list=[
                    EndpointSearchResultOut(
                        endpoint=_endpoint_out(instance),
                        api=_api_summary_out(instance.api),
                    )
                    for instance in page.object_list
                ],
            ),
        )


# --- Operation ----------------------
#
# Read-only: only the two `GET` views
# below exist, each gated on `operation.read`
# (`check_operation_read_permission`), the same way the Endpoint reads above
# are gated on `endpoint.read` — `Operation` isn't a registered Entity Kind
# either, so it gets none of the generic per-kind permission wiring `api`
# itself gets.


def _operation_provider_service(api: CatalogEntity) -> CatalogEntity | None:
    """The API document's own owning Service, found via its `apiProvidedBy`
    relation — `None` if the API has no declared provider."""
    provider_relation = next(
        (
            relation
            for relation in entity_relations(api)
            if relation[0] == "apiProvidedBy"
        ),
        None,
    )
    if provider_relation is None:
        return None
    _predicate, _ref, _kind, provider_id = provider_relation
    return (
        get_catalog_entity_model().objects.select_related("owner").get(pk=provider_id)
    )


def _operation_provider_out(
    provider: CatalogEntity | None, direction: str
) -> OperationProviderOut | None:
    """The provider Service's role, implied purely from the Operation's
    `direction` — `send` implies publisher, `receive`
    implies subscriber — never a stored `ServiceOperationUsage` row."""
    if provider is None:
        return None
    role = "publisher" if direction == ApiOperation.DIRECTION_SEND else "subscriber"
    return OperationProviderOut(service=_service_summary_out(provider), role=role)


def _operation_out(
    instance: ApiOperation, provider: CatalogEntity | None
) -> OperationOut:
    return OperationOut(
        id=instance.id,
        api_id=instance.api_id,
        channel_address=instance.channel_address,
        channel_protocol=instance.channel_protocol,
        direction=instance.direction,
        operation_key=instance.operation_key,
        operation_id=instance.operation_id,
        summary=instance.summary,
        description=instance.description,
        tags=instance.tags,
        messages=[
            OperationMessageOut.model_validate(message) for message in instance.message
        ],
        external_docs=ExternalDocsOut.model_validate(instance.external_docs)
        if instance.external_docs
        else None,
        status=instance.status,
        deprecated=instance.deprecated,
        provider=_operation_provider_out(provider, instance.direction),
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


def _get_operation(api: CatalogEntity, operation_id) -> ApiOperation:
    try:
        return ApiOperation.objects.get(pk=operation_id, api_id=api.id)
    except ApiOperation.DoesNotExist:
        raise APIError(
            format_error("Operation not found", error_type=ErrorType.not_found),
            status_code=HTTPStatus.NOT_FOUND,
        ) from None


class ApiOperationListController(AtlasController):
    auth = (SessionAuth(),)

    def get(
        self,
        parsed_path: Path[ApiOperationsPath],
        parsed_query: Query[ApiOperationListQuery],
    ) -> list[OperationOut]:
        check_operation_read_permission(self.request.user)
        api = _get_api(parsed_path.api_id)
        queryset = ApiOperation.objects.filter(
            api_id=api.id, status=parsed_query.status
        )
        if parsed_query.direction:
            queryset = queryset.filter(direction=parsed_query.direction)
        if parsed_query.tag:
            queryset = queryset.filter(tags__contains=[parsed_query.tag])
        if parsed_query.search:
            queryset = queryset.filter(
                Q(channel_address__icontains=parsed_query.search)
                | Q(summary__icontains=parsed_query.search)
                | Q(operation_id__icontains=parsed_query.search),
            )
        provider = _operation_provider_service(api)
        return [_operation_out(instance, provider) for instance in queryset]


class ApiOperationDetailController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[ApiOperationPath]) -> OperationOut:
        check_operation_read_permission(self.request.user)
        api = _get_api(parsed_path.api_id)
        operation = _get_operation(api, parsed_path.id)
        return _operation_out(operation, _operation_provider_service(api))


class ApiOperationPurgeController(AtlasController):
    """Purge a removed Operation
    — mirrors `ApiEndpointPurgeController` exactly, one level down."""

    auth = (SessionAuth(),)

    @modify(status_code=HTTPStatus.NO_CONTENT, extra_responses=[FORBIDDEN_RESPONSE])
    def post(self, parsed_path: Path[ApiOperationPath]) -> None:
        api = _get_api(parsed_path.api_id)
        operation = _get_operation(api, parsed_path.id)
        check_operation_purge_permission(self.request.user, api)
        if operation.status != ApiOperation.STATUS_REMOVED:
            raise delete_blocked(
                "Cannot purge this Operation: only a removed Operation may be purged"
            )
        blocking = [
            f"Service {usage.service.name!r}"
            for usage in ServiceOperationUsage.objects.filter(
                operation=operation
            ).select_related("service")
            if usage.service.status == STATUS_ACTIVE
        ]
        if blocking:
            raise delete_blocked(
                f"Cannot purge this Operation: still referenced by {', '.join(blocking)}"
            )
        with transaction.atomic():
            # `ServiceOperationUsage.operation`'s `on_delete=CASCADE` cleans
            # up every remaining (already-removed-Service-only) link
            # automatically — no separate cascade step needed.
            operation.delete()


class ApiOperationSearchController(AtlasController):
    """Cross-API Operation search — mirrors `ApiEndpointSearchController` exactly, backing the
    Flow "Add Step" Event picker. `provider` is omitted (never resolved) for
    each result — deriving it per API via `_operation_provider_service()`
    would cost one extra relation lookup per matching API on every
    keystroke, for a field the picker doesn't render."""

    auth = (SessionAuth(),)

    def get(
        self, parsed_query: Query[ApiOperationSearchQuery]
    ) -> PaginatedOut[OperationSearchResultOut]:
        check_operation_read_permission(self.request.user)
        queryset = ApiOperation.objects.filter(
            status=ApiOperation.STATUS_ACTIVE
        ).select_related("api")
        if parsed_query.search:
            queryset = queryset.filter(
                Q(channel_address__icontains=parsed_query.search)
                | Q(summary__icontains=parsed_query.search)
                | Q(operation_id__icontains=parsed_query.search),
            )
        page = Paginator(queryset, parsed_query.page_size).page(parsed_query.page)
        return PaginatedOut(
            count=page.paginator.count,
            num_pages=page.paginator.num_pages,
            per_page=page.paginator.per_page,
            page=PageOut(
                number=page.number,
                object_list=[
                    OperationSearchResultOut(
                        operation=_operation_out(instance, None),
                        api=_api_summary_out(instance.api),
                    )
                    for instance in page.object_list
                ],
            ),
        )


# --- Service <-> Endpoint dependency ---------------------------------------------------
#
# Routed top-level under `/api/endpoints/{endpointId}/...`, not nested under
# `/api/apis/{apiId}/...` like the read-only Endpoint views above — a
# `ServiceEndpointUsage` link is addressed by its Endpoint alone, the same
# way its route list gives it (`GET`/`POST
# /api/endpoints/{endpointId}/services`, `DELETE .../services/{serviceId}`,
# `GET .../consumers`).

CONFLICT_RESPONSE = ResponseSpec(
    ErrorModel,
    status_code=HTTPStatus.CONFLICT,
    description="This Service is already linked to this Endpoint",
)


def _conflict(message: str) -> APIError:
    return APIError(
        format_error(message, error_type=ErrorType.value_error),
        status_code=HTTPStatus.CONFLICT,
    )


def _get_endpoint_by_id(endpoint_id) -> ApiEndpoint:
    try:
        return ApiEndpoint.objects.select_related("api").get(pk=endpoint_id)
    except ApiEndpoint.DoesNotExist:
        raise APIError(
            format_error("Endpoint not found", error_type=ErrorType.not_found),
            status_code=HTTPStatus.NOT_FOUND,
        ) from None


def _get_service(service_id) -> CatalogEntity:
    catalog_entity_model = get_catalog_entity_model()
    try:
        return catalog_entity_model.objects.select_related("owner").get(
            pk=service_id,
            kind=KIND_COMPONENT,
        )
    except catalog_entity_model.DoesNotExist:
        raise APIError(
            format_error("Service not found", error_type=ErrorType.not_found),
            status_code=HTTPStatus.NOT_FOUND,
        ) from None


def _service_summary_out(service: CatalogEntity) -> ServiceSummaryOut:
    team = service.owner
    return ServiceSummaryOut(
        id=service.id,
        ref=service.ref,
        name=service.name,
        title=service.title,
        team=team.ref,
        team_id=team.id,
        team_name=team.title or team.name,
    )


def _endpoint_service_out(usage: ServiceEndpointUsage) -> EndpointServiceOut:
    return EndpointServiceOut(
        id=usage.id,
        service=_service_summary_out(usage.service),
        linked_at=usage.created_at,
    )


_ENDPOINT_SERVICE_SORT_FIELDS = {
    "service": "service__title",
    "team": "service__owner__title",
}


class EndpointServicesController(AtlasController):
    auth = (SessionAuth(),)

    def get(
        self,
        parsed_path: Path[EndpointServicesPath],
        parsed_query: Query[EndpointServicesQuery],
    ) -> PaginatedOut[EndpointServiceOut]:
        check_endpoint_dependency_read_permission(self.request.user)
        endpoint = _get_endpoint_by_id(parsed_path.endpoint_id)
        queryset = ServiceEndpointUsage.objects.filter(
            endpoint=endpoint,
        ).select_related("service", "service__owner")
        if parsed_query.search:
            queryset = queryset.filter(
                Q(service__title__icontains=parsed_query.search)
                | Q(service__name__icontains=parsed_query.search),
            )
        if parsed_query.team_id:
            queryset = queryset.filter(service__owner_id=parsed_query.team_id)
        sort_field = _ENDPOINT_SERVICE_SORT_FIELDS[parsed_query.sort]
        tiebreakers = ["service__name", "id"]
        if parsed_query.order == "desc":
            sort_field = f"-{sort_field}"
            tiebreakers = [f"-{field}" for field in tiebreakers]
        page = Paginator(
            queryset.order_by(sort_field, *tiebreakers),
            parsed_query.page_size,
        ).page(parsed_query.page)
        return PaginatedOut(
            count=page.paginator.count,
            num_pages=page.paginator.num_pages,
            per_page=page.paginator.per_page,
            page=PageOut(
                number=page.number,
                object_list=[
                    _endpoint_service_out(usage) for usage in page.object_list
                ],
            ),
        )

    @modify(extra_responses=[FORBIDDEN_RESPONSE, CONFLICT_RESPONSE])
    def post(
        self,
        parsed_path: Path[EndpointServicesPath],
        parsed_body: Body[EndpointServiceLinkIn],
    ) -> EndpointServiceLinkOut:
        endpoint = _get_endpoint_by_id(parsed_path.endpoint_id)
        service = _get_service(parsed_body.service_id)
        check_endpoint_dependency_create_permission(self.request.user, service)
        if endpoint.status == ApiEndpoint.STATUS_REMOVED:
            raise _conflict(
                "This Endpoint has been removed and cannot receive new links"
            )
        already_linked = ServiceEndpointUsage.objects.filter(
            endpoint=endpoint,
            service=service,
        ).exists()
        if already_linked:
            raise _conflict("This Service is already linked to this Endpoint")
        with transaction.atomic():
            usage = ServiceEndpointUsage.objects.create(
                endpoint=endpoint,
                service=service,
                created_by=self.request.user,
            )
            api_relation_created = add_consumed_api(service, endpoint.api)
        return EndpointServiceLinkOut(
            id=usage.id,
            service=_service_summary_out(service),
            linked_at=usage.created_at,
            api_relation_created=api_relation_created,
        )


class EndpointServiceController(AtlasController):
    auth = (SessionAuth(),)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def delete(self, parsed_path: Path[EndpointServicePath]) -> None:
        endpoint = _get_endpoint_by_id(parsed_path.endpoint_id)
        try:
            usage = ServiceEndpointUsage.objects.select_related(
                "service", "service__owner"
            ).get(
                endpoint=endpoint,
                service_id=parsed_path.service_id,
            )
        except ServiceEndpointUsage.DoesNotExist:
            raise APIError(
                format_error(
                    "Service is not linked to this Endpoint",
                    error_type=ErrorType.not_found,
                ),
                status_code=HTTPStatus.NOT_FOUND,
            ) from None
        check_endpoint_dependency_delete_permission(self.request.user, usage.service)
        # `consumesAPI` is untouched (unlinking does not remove
        # consumesAPI) — the Service may still consume other Endpoints of
        # the same API, or have a hand-authored `consumesAPI`.
        usage.delete()


class EndpointConsumersController(AtlasController):
    auth = (SessionAuth(),)

    def get(
        self,
        parsed_path: Path[EndpointServicesPath],
    ) -> EndpointConsumersOut:
        check_endpoint_dependency_read_permission(self.request.user)
        endpoint = _get_endpoint_by_id(parsed_path.endpoint_id)
        usages = (
            ServiceEndpointUsage.objects.filter(
                endpoint=endpoint,
            )
            .select_related("service", "service__owner")
            .order_by(
                "service__title",
                "service__name",
            )
        )
        return EndpointConsumersOut(
            endpoint=EndpointConsumerSummaryOut(
                id=endpoint.id,
                method=endpoint.method,
                path=endpoint.path,
                status=endpoint.status,
            ),
            services=[_service_summary_out(usage.service) for usage in usages],
        )


# --- Service <-> Operation dependency ---------------------------------------------------
#
# Routed top-level under `/api/operations/{operationId}/...`, not nested
# under `/api/apis/{apiId}/...` like the read-only Operation views above —
# same routing shape as `ServiceEndpointUsage`'s own controllers.


def _get_operation_by_id(operation_id) -> ApiOperation:
    try:
        return ApiOperation.objects.select_related("api").get(pk=operation_id)
    except ApiOperation.DoesNotExist:
        raise APIError(
            format_error("Operation not found", error_type=ErrorType.not_found),
            status_code=HTTPStatus.NOT_FOUND,
        ) from None


def _operation_service_out(usage: ServiceOperationUsage) -> OperationServiceOut:
    return OperationServiceOut(
        id=usage.id,
        service=_service_summary_out(usage.service),
        role=usage.role,
        linked_at=usage.created_at,
    )


_OPERATION_SERVICE_SORT_FIELDS = {
    "service": "service__title",
    "team": "service__owner__title",
}


class OperationServicesController(AtlasController):
    auth = (SessionAuth(),)

    def get(
        self,
        parsed_path: Path[OperationServicesPath],
        parsed_query: Query[OperationServicesQuery],
    ) -> PaginatedOut[OperationServiceOut]:
        check_operation_dependency_read_permission(self.request.user)
        operation = _get_operation_by_id(parsed_path.operation_id)
        queryset = ServiceOperationUsage.objects.filter(
            operation=operation,
        ).select_related("service", "service__owner")
        if parsed_query.search:
            queryset = queryset.filter(
                Q(service__title__icontains=parsed_query.search)
                | Q(service__name__icontains=parsed_query.search),
            )
        if parsed_query.team_id:
            queryset = queryset.filter(service__owner_id=parsed_query.team_id)
        if parsed_query.role:
            queryset = queryset.filter(role=parsed_query.role)
        sort_field = _OPERATION_SERVICE_SORT_FIELDS[parsed_query.sort]
        tiebreakers = ["service__name", "id"]
        if parsed_query.order == "desc":
            sort_field = f"-{sort_field}"
            tiebreakers = [f"-{field}" for field in tiebreakers]
        page = Paginator(
            queryset.order_by(sort_field, *tiebreakers),
            parsed_query.page_size,
        ).page(parsed_query.page)
        return PaginatedOut(
            count=page.paginator.count,
            num_pages=page.paginator.num_pages,
            per_page=page.paginator.per_page,
            page=PageOut(
                number=page.number,
                object_list=[
                    _operation_service_out(usage) for usage in page.object_list
                ],
            ),
        )

    @modify(extra_responses=[FORBIDDEN_RESPONSE, CONFLICT_RESPONSE])
    def post(
        self,
        parsed_path: Path[OperationServicesPath],
        parsed_body: Body[OperationServiceLinkIn],
    ) -> OperationServiceLinkOut:
        operation = _get_operation_by_id(parsed_path.operation_id)
        service = _get_service(parsed_body.service_id)
        check_operation_dependency_create_permission(self.request.user, service)
        provider = _operation_provider_service(operation.api)
        if provider is not None and provider.id == service.id:
            raise _conflict(
                "This Service is the Operation's own document owner — its role is "
                "already implied by the Operation's direction and cannot be linked",
            )
        already_linked = ServiceOperationUsage.objects.filter(
            operation=operation,
            service=service,
            role=parsed_body.role,
        ).exists()
        if already_linked:
            raise _conflict(
                "This Service is already linked to this Operation with this role",
            )
        usage = ServiceOperationUsage.objects.create(
            operation=operation,
            service=service,
            role=parsed_body.role,
            created_by=self.request.user,
        )
        return OperationServiceLinkOut(
            id=usage.id,
            service=_service_summary_out(service),
            role=usage.role,
            linked_at=usage.created_at,
        )


class OperationServiceController(AtlasController):
    auth = (SessionAuth(),)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def delete(
        self,
        parsed_path: Path[OperationServicePath],
        parsed_query: Query[OperationServiceDeleteQuery],
    ) -> None:
        operation = _get_operation_by_id(parsed_path.operation_id)
        try:
            usage = ServiceOperationUsage.objects.select_related(
                "service", "service__owner"
            ).get(
                operation=operation,
                service_id=parsed_path.service_id,
                role=parsed_query.role,
            )
        except ServiceOperationUsage.DoesNotExist:
            raise APIError(
                format_error(
                    "Service is not linked to this Operation with this role",
                    error_type=ErrorType.not_found,
                ),
                status_code=HTTPStatus.NOT_FOUND,
            ) from None
        check_operation_dependency_delete_permission(self.request.user, usage.service)
        # Only the targeted `(operation, service, role)` row is removed
        # a Service holding both roles keeps its
        # other role's row intact.
        usage.delete()


def _channel_participants(
    operations: list[ApiOperation],
) -> list[OperationConsumerParticipantOut]:
    """Every publisher/subscriber for a channel, aggregated across every
    `ApiOperation` sharing it — each operation's own
    document-owner implied role, plus every explicit `ServiceOperationUsage`
    row, deduplicated by (service, role) since the same Service can
    independently reach the same role from more than one contributing
    operation."""
    apis_by_id = {}
    for operation in operations:
        apis_by_id.setdefault(operation.api_id, operation.api)
    providers = {
        api_id: _operation_provider_service(api) for api_id, api in apis_by_id.items()
    }
    seen: set[tuple] = set()
    participants: list[OperationConsumerParticipantOut] = []
    for operation in operations:
        provider = providers[operation.api_id]
        if provider is None:
            continue
        role = (
            "publisher"
            if operation.direction == ApiOperation.DIRECTION_SEND
            else "subscriber"
        )
        key = (provider.id, role)
        if key in seen:
            continue
        seen.add(key)
        participants.append(
            OperationConsumerParticipantOut(
                service=_service_summary_out(provider), role=role
            )
        )
    usages = ServiceOperationUsage.objects.filter(
        operation__in=operations,
    ).select_related("service", "service__owner")
    for usage in usages:
        key = (usage.service_id, usage.role)
        if key in seen:
            continue
        seen.add(key)
        participants.append(
            OperationConsumerParticipantOut(
                service=_service_summary_out(usage.service), role=usage.role
            ),
        )
    return participants


class OperationConsumersController(AtlasController):
    auth = (SessionAuth(),)

    def get(
        self,
        parsed_path: Path[OperationServicesPath],
    ) -> OperationConsumersOut:
        check_operation_dependency_read_permission(self.request.user)
        operation = _get_operation_by_id(parsed_path.operation_id)
        aggregated = list(
            ApiOperation.objects.filter(
                channel_address=operation.channel_address,
            ).select_related("api", "api__owner"),
        )
        return OperationConsumersOut(
            operation=OperationConsumerSummaryOut(
                id=operation.id,
                channel_address=operation.channel_address,
                channel_protocol=operation.channel_protocol,
                direction=operation.direction,
                status=operation.status,
            ),
            participants=_channel_participants(aggregated),
        )
