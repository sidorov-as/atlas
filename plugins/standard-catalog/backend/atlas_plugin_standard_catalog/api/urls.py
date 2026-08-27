"""URL routing for System/Component/Resource/Group/Actor —
split out of `server.apps.catalog.api.urls`.
Included alongside the core `catalog_router` from `server/urls.py`.
"""

from dmr.routing import Router, path

from .views import (
    ActorDetailController,
    ActorListController,
    ActorRelationsController,
    ComponentAdoptController,
    ComponentDetailController,
    ComponentHistoryController,
    ComponentListController,
    ComponentPurgeController,
    ComponentRelationsController,
    ComponentRemoveController,
    ComponentReviveController,
    GroupDetailController,
    GroupListController,
    GroupRelationsController,
    ResourceAdoptController,
    ResourceDetailController,
    ResourceHistoryController,
    ResourceListController,
    ResourcePurgeController,
    ResourceRelationsController,
    ResourceRemoveController,
    ResourceReviveController,
    SystemAdoptController,
    SystemDetailController,
    SystemDocumentLinksController,
    SystemHistoryController,
    SystemListController,
    SystemPurgeController,
    SystemRelationsController,
    SystemRemoveController,
    SystemReviveController,
)

router = Router(
    "api/",
    [
        path("systems/", SystemListController.as_view(), name="system-list"),
        path(
            "systems/<uuid:id>/", SystemDetailController.as_view(), name="system-detail"
        ),
        path(
            "systems/<uuid:id>/docs/",
            SystemDocumentLinksController.as_view(),
            name="system-document-links",
        ),
        path(
            "systems/<uuid:id>/relations/",
            SystemRelationsController.as_view(),
            name="system-relations",
        ),
        path(
            "systems/<uuid:id>/history/",
            SystemHistoryController.as_view(),
            name="system-history",
        ),
        path(
            "systems/<uuid:id>/adopt/",
            SystemAdoptController.as_view(),
            name="system-adopt",
        ),
        path(
            "systems/<uuid:id>/remove/",
            SystemRemoveController.as_view(),
            name="system-remove",
        ),
        path(
            "systems/<uuid:id>/revive/",
            SystemReviveController.as_view(),
            name="system-revive",
        ),
        path(
            "systems/<uuid:id>/purge/",
            SystemPurgeController.as_view(),
            name="system-purge",
        ),
        path("components/", ComponentListController.as_view(), name="component-list"),
        path(
            "components/<uuid:id>/",
            ComponentDetailController.as_view(),
            name="component-detail",
        ),
        path(
            "components/<uuid:id>/relations/",
            ComponentRelationsController.as_view(),
            name="component-relations",
        ),
        path(
            "components/<uuid:id>/history/",
            ComponentHistoryController.as_view(),
            name="component-history",
        ),
        path(
            "components/<uuid:id>/adopt/",
            ComponentAdoptController.as_view(),
            name="component-adopt",
        ),
        path(
            "components/<uuid:id>/remove/",
            ComponentRemoveController.as_view(),
            name="component-remove",
        ),
        path(
            "components/<uuid:id>/revive/",
            ComponentReviveController.as_view(),
            name="component-revive",
        ),
        path(
            "components/<uuid:id>/purge/",
            ComponentPurgeController.as_view(),
            name="component-purge",
        ),
        path("resources/", ResourceListController.as_view(), name="resource-list"),
        path(
            "resources/<uuid:id>/",
            ResourceDetailController.as_view(),
            name="resource-detail",
        ),
        path(
            "resources/<uuid:id>/relations/",
            ResourceRelationsController.as_view(),
            name="resource-relations",
        ),
        path(
            "resources/<uuid:id>/history/",
            ResourceHistoryController.as_view(),
            name="resource-history",
        ),
        path(
            "resources/<uuid:id>/adopt/",
            ResourceAdoptController.as_view(),
            name="resource-adopt",
        ),
        path(
            "resources/<uuid:id>/remove/",
            ResourceRemoveController.as_view(),
            name="resource-remove",
        ),
        path(
            "resources/<uuid:id>/revive/",
            ResourceReviveController.as_view(),
            name="resource-revive",
        ),
        path(
            "resources/<uuid:id>/purge/",
            ResourcePurgeController.as_view(),
            name="resource-purge",
        ),
        path("groups/", GroupListController.as_view(), name="group-list"),
        path("groups/<uuid:id>/", GroupDetailController.as_view(), name="group-detail"),
        path(
            "groups/<uuid:id>/relations/",
            GroupRelationsController.as_view(),
            name="group-relations",
        ),
        path("users/", ActorListController.as_view(), name="user-list"),
        path("users/<uuid:id>/", ActorDetailController.as_view(), name="user-detail"),
        path(
            "users/<uuid:id>/relations/",
            ActorRelationsController.as_view(),
            name="user-relations",
        ),
    ],
)
