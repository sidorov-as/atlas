"""URL routing for the Database Schema facet endpoint — a specialized,
non-generic-entity-CRUD namespace (`/api/plugins/atlas.database-
schema/...`), mirroring the convention the C4 plugin established.
Included from `server/urls.py` only when this optional plugin is selected
(Database Schema is an optional plugin).
"""

from dmr.routing import Router, path

from .views import DatabaseSchemaController

router = Router(
    "api/plugins/atlas.database-schema/",
    [
        path(
            "resources/<uuid:id>/schema/",
            DatabaseSchemaController.as_view(),
            name="database-schema",
        ),
    ],
)
