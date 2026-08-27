"""URL routing for the entity CRUD API still owned by `server.apps.catalog`
System/Component/Resource/Group/Actor routes moved to
`atlas_plugin_standard_catalog.api.urls`,
API routes moved to `atlas_plugin_apis.api.urls`,
diagram routes moved to `atlas_plugin_c4.api.urls`, Flow
routes moved to `atlas_plugin_flows.api.urls`;
`server/urls.py` includes all five routers.
"""

from dmr.routing import Router, path

from .views import (
    ArchitectureRelationshipDetailController,
    ArchitectureRelationshipListController,
    CatalogHomeSettingsController,
    MeController,
    TagDetailController,
    TagListController,
)

router = Router(
    "api/",
    [
        path(
            "catalog-home-settings/",
            CatalogHomeSettingsController.as_view(),
            name="catalog-home-settings",
        ),
        path("me/", MeController.as_view(), name="me"),
        path(
            "architecture-relationships/",
            ArchitectureRelationshipListController.as_view(),
            name="architecture-relationship-list",
        ),
        path(
            "architecture-relationships/<int:id>/",
            ArchitectureRelationshipDetailController.as_view(),
            name="architecture-relationship-detail",
        ),
        path("tags/", TagListController.as_view(), name="tag-list"),
        path(
            "tags/<int:id>/", TagDetailController.as_view(), name="tag-detail"
        ),
    ],
)
