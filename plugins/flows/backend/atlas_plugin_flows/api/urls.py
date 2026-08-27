"""URL routing for Flow — split out of
`server.apps.catalog.api.urls`. Included from
`server/urls.py`, gated on `atlas_plugin_flows` being installed, at the same
`flows/` path it had before this extraction.
"""

from dmr.routing import Router, path

from .views import FlowDetailController, FlowListController

router = Router(
    "api/",
    [
        path("flows/", FlowListController.as_view(), name="flow-list"),
        path("flows/<int:id>/", FlowDetailController.as_view(), name="flow-detail"),
    ],
)
