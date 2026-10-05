"""Routes under `/api/plugins/atlas.search/`; mounted by `server/urls.py` only
when the plugin's app is installed."""

from dmr.routing import Router, path

from .views import SearchController, StatusController

router = Router(
    "api/plugins/atlas.search/",
    [
        path("search/", SearchController.as_view(), name="search"),
        path("status/", StatusController.as_view(), name="search-status"),
    ],
)
