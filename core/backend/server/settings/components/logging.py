from collections.abc import Callable

import structlog

from server.apps.catalog.auth_security import redact_authentication_event

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                redact_authentication_event,
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
            "foreign_pre_chain": [redact_authentication_event],
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "console"}
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}


class LoggingContextVarsMiddleware:
    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        structlog.contextvars.clear_contextvars()
        return response
