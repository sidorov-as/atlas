"""URL routing for the MCP API — a scoped `dmr` controller module distinct
from every other plugin's SPA-facing API, mounted under its own
`/api/plugins/atlas.mcp/` prefix (the same non-generic-entity-CRUD
convention `atlas_plugin_c4.api.urls` documents).

`build_router()` (re)builds this API's `Router` fresh on every call rather
than freezing its route list at this module's first import: whether the
Flow (and API Endpoint/Operation) routes are present depends on whether
`atlas.flows` (`atlas.apis`) is installed *right now*, checked via
`django.apps.apps.is_installed` the same way
`atlas_plugin_standard_catalog.kinds`/`atlas_plugin_flows.models` already
check their own optional link to `atlas.apis` — a call-time check, not an
import-time one, so `atlas_plugin_mcp.api.openapi.build_openapi_schema()`
(and its own test) can flip that answer with a simple monkeypatch instead
of reloading this module. `router`, the module-level instance `server/urls.py`
actually mounts, is just `build_router()` called once at process start,
after every plugin's Django app is already registered.
"""

from django.apps import apps as django_apps
from dmr.routing import Router, external_path, path

from .schema_views import openapi_schema_view
from .views import (
    CreateEntityController,
    EntityDetailController,
    EntityPurgeController,
    EntityRemoveController,
    SearchCatalogController,
)

_CATALOG_URLS = [
    path(
        "catalog/search/", SearchCatalogController.as_view(), name="mcp-search-catalog"
    ),
    path("catalog/", CreateEntityController.as_view(), name="mcp-create-entity"),
    path("catalog/<uuid:id>/", EntityDetailController.as_view(), name="mcp-get-entity"),
    path(
        "catalog/<uuid:id>/remove/",
        EntityRemoveController.as_view(),
        name="mcp-remove-entity",
    ),
    path(
        "catalog/<uuid:id>/purge/",
        EntityPurgeController.as_view(),
        name="mcp-purge-entity",
    ),
    # `openapi=None` keeps this plugin's own schema document out of the
    # document it serves — a plain Django view (see `schema_views`'s
    # docstring), not a `Controller`, so it has no operation metadata of its
    # own for `get_schema()` to collect anyway.
    external_path(
        "openapi.json", openapi_schema_view, openapi=None, name="mcp-openapi-schema"
    ),
]


def _flow_urls() -> list:
    if not django_apps.is_installed("atlas_plugin_flows"):
        return []

    from .flow_views import FlowDetailController, FlowListController

    return [
        path("flows/", FlowListController.as_view(), name="mcp-list-flows"),
        path("flows/<int:id>/", FlowDetailController.as_view(), name="mcp-get-flow"),
    ]


def _api_urls() -> list:
    if not django_apps.is_installed("atlas_plugin_apis"):
        return []

    from .endpoint_views import (
        EndpointConsumersController,
        EndpointDetailController,
        EndpointSearchController,
        OperationConsumersController,
        OperationDetailController,
        OperationSearchController,
    )

    return [
        path(
            "endpoints/search/",
            EndpointSearchController.as_view(),
            name="mcp-search-api-endpoints",
        ),
        path(
            "endpoints/<uuid:id>/",
            EndpointDetailController.as_view(),
            name="mcp-get-api-endpoint",
        ),
        path(
            "endpoints/<uuid:id>/consumers/",
            EndpointConsumersController.as_view(),
            name="mcp-get-endpoint-consumers",
        ),
        path(
            "operations/search/",
            OperationSearchController.as_view(),
            name="mcp-search-api-operations",
        ),
        path(
            "operations/<uuid:id>/",
            OperationDetailController.as_view(),
            name="mcp-get-api-operation",
        ),
        path(
            "operations/<uuid:id>/consumers/",
            OperationConsumersController.as_view(),
            name="mcp-get-operation-consumers",
        ),
    ]


def build_router() -> Router:
    return Router(
        "api/plugins/atlas.mcp/",
        [*_CATALOG_URLS, *_flow_urls(), *_api_urls()],
    )


router = build_router()
