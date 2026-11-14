"""URL routing for the diagram endpoints — included from
`server/urls.py` under a specialized, non-generic-entity-CRUD namespace
(`/api/plugins/atlas.c4/...`, following the
illustrative convention), rather than reusing the flat `api/` prefix core and
the other plugins share.
"""

from dmr.routing import Router, path

from .views import (
    ActorKindsController,
    CustomViewDiagramController,
    DiagramController,
    SystemLandscapeDiagramController,
    ViewDetailController,
    ViewDiagramController,
    ViewListController,
)

router = Router(
    "api/plugins/atlas.c4/",
    [
        path(
            "diagrams/landscape/",
            SystemLandscapeDiagramController.as_view(),
            name="system-landscape-diagram",
        ),
        path(
            "diagrams/custom/",
            CustomViewDiagramController.as_view(),
            name="custom-view-diagram",
        ),
        path(
            "custom-view/actor-kinds/",
            ActorKindsController.as_view(),
            name="custom-view-actor-kinds",
        ),
        path("views/", ViewListController.as_view(), name="views"),
        path("views/<uuid:id>/", ViewDetailController.as_view(), name="view"),
        path(
            "views/<uuid:id>/diagram/",
            ViewDiagramController.as_view(),
            name="view-diagram",
        ),
        path(
            "diagrams/<str:kind>/<uuid:id>/",
            DiagramController.as_view(),
            name="diagram",
        ),
    ],
)
