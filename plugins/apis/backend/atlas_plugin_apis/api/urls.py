"""URL routing for the API kind — split out of
`server.apps.catalog.api.urls`. Included alongside the
core `catalog_router` and Standard Catalog's `standard_catalog_router` from
`server/urls.py`.
"""

from dmr.routing import Router, path

from .views import (
    ApiAdoptController,
    ApiDetailController,
    ApiEndpointDetailController,
    ApiEndpointListController,
    ApiEndpointPurgeController,
    ApiEndpointSearchController,
    ApiHistoryController,
    ApiListController,
    ApiOperationDetailController,
    ApiOperationListController,
    ApiOperationPurgeController,
    ApiOperationSearchController,
    ApiPurgeController,
    ApiRelationsController,
    ApiRemoveController,
    ApiReviveController,
    EndpointConsumersController,
    EndpointServiceController,
    EndpointServicesController,
    OperationConsumersController,
    OperationServiceController,
    OperationServicesController,
)

router = Router(
    "api/",
    [
        path("apis/", ApiListController.as_view(), name="api-list"),
        path("apis/<uuid:id>/", ApiDetailController.as_view(), name="api-detail"),
        path(
            "apis/<uuid:id>/relations/",
            ApiRelationsController.as_view(),
            name="api-relations",
        ),
        path(
            "apis/<uuid:id>/history/",
            ApiHistoryController.as_view(),
            name="api-history",
        ),
        path("apis/<uuid:id>/adopt/", ApiAdoptController.as_view(), name="api-adopt"),
        path(
            "apis/<uuid:id>/remove/", ApiRemoveController.as_view(), name="api-remove"
        ),
        path(
            "apis/<uuid:id>/revive/", ApiReviveController.as_view(), name="api-revive"
        ),
        path("apis/<uuid:id>/purge/", ApiPurgeController.as_view(), name="api-purge"),
        path(
            "apis/endpoints/search/",
            ApiEndpointSearchController.as_view(),
            name="api-endpoint-search",
        ),
        path(
            "apis/operations/search/",
            ApiOperationSearchController.as_view(),
            name="api-operation-search",
        ),
        path(
            "apis/<uuid:api_id>/endpoints/",
            ApiEndpointListController.as_view(),
            name="api-endpoint-list",
        ),
        path(
            "apis/<uuid:api_id>/endpoints/<uuid:id>/",
            ApiEndpointDetailController.as_view(),
            name="api-endpoint-detail",
        ),
        path(
            "apis/<uuid:api_id>/endpoints/<uuid:id>/purge/",
            ApiEndpointPurgeController.as_view(),
            name="api-endpoint-purge",
        ),
        path(
            "apis/<uuid:api_id>/operations/",
            ApiOperationListController.as_view(),
            name="api-operation-list",
        ),
        path(
            "apis/<uuid:api_id>/operations/<uuid:id>/",
            ApiOperationDetailController.as_view(),
            name="api-operation-detail",
        ),
        path(
            "apis/<uuid:api_id>/operations/<uuid:id>/purge/",
            ApiOperationPurgeController.as_view(),
            name="api-operation-purge",
        ),
        path(
            "endpoints/<uuid:endpoint_id>/services/",
            EndpointServicesController.as_view(),
            name="endpoint-service-list",
        ),
        path(
            "endpoints/<uuid:endpoint_id>/services/<uuid:service_id>/",
            EndpointServiceController.as_view(),
            name="endpoint-service-detail",
        ),
        path(
            "endpoints/<uuid:endpoint_id>/consumers/",
            EndpointConsumersController.as_view(),
            name="endpoint-consumers",
        ),
        path(
            "operations/<uuid:operation_id>/services/",
            OperationServicesController.as_view(),
            name="operation-service-list",
        ),
        path(
            "operations/<uuid:operation_id>/services/<uuid:service_id>/",
            OperationServiceController.as_view(),
            name="operation-service-detail",
        ),
        path(
            "operations/<uuid:operation_id>/consumers/",
            OperationConsumersController.as_view(),
            name="operation-consumers",
        ),
    ],
)
