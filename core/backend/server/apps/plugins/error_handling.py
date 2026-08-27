"""Project-wide DMR `global_error_handler` (`runtime-failure-isolation` spec:
"An internal failure in one plugin-owned endpoint SHALL return a clean
degraded response ... SHALL NOT affect requests to other plugins' or core's
endpoints").

Every controller in this codebase — Core's and every plugin's alike — is an
`AtlasController` (`server.apps.catalog.api.helpers.AtlasController`), none
of which override `handle_error`/`handle_async_error`, so an exception a
view doesn't catch itself always reaches this module's `global_error_handler`
(wired in via `DMR_SETTINGS[Settings.global_error_handler]`,
`settings/components/api.py`) rather than propagating past the controller
framework as a raw, unhandled traceback. dmr's own default handler already
turns a known, framework-level exception (`ValidationError`,
`NotAuthenticatedError`, ...) into a typed response; this wraps it so an
*unknown* exception — a genuine bug in a plugin's view or business logic —
gets the same typed, DEBUG-gated treatment as `dmr.exceptions.
InternalServerError` instead of reaching Django's raw error page.
"""

import logging

from dmr.errors import format_error
from dmr.errors import global_error_handler as dmr_global_error_handler
from dmr.exceptions import InternalServerError

from server.apps.plugins.health import mark_degraded, plugin_id_for_module

logger = logging.getLogger("atlas.plugins.error_handling")


def global_error_handler(endpoint, controller, exc):
    try:
        return dmr_global_error_handler(endpoint, controller, exc)
    except Exception:
        logger.exception("Unhandled exception in %s", endpoint)
        plugin_id = plugin_id_for_module(type(controller).__module__)
        if plugin_id is not None:
            mark_degraded(plugin_id, str(exc))
        return controller.to_error(
            format_error(InternalServerError(str(exc))),
            status_code=InternalServerError.status_code,
        )
