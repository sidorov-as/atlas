"""URL routing for the diagram endpoints — included from
`server/urls.py` under a specialized, non-generic-entity-CRUD namespace
(`/api/plugins/atlas.c4/...`, following the
illustrative convention), rather than reusing the flat `api/` prefix core and
the other plugins share.
"""

from dmr.routing import Router, path

from .views import DiagramController, SystemLandscapeDiagramController

router = Router(
    "api/plugins/atlas.c4/",
    [
        path(
            "diagrams/landscape/",
            SystemLandscapeDiagramController.as_view(),
            name="system-landscape-diagram",
        ),
        path(
            "diagrams/<str:kind>/<uuid:id>/",
            DiagramController.as_view(),
            name="diagram",
        ),
    ],
)
