from collections.abc import Callable

import structlog

from server.apps.catalog.auth_security import redact_authentication_event
from server.settings.components import config

# Tracebacks are off by default: redaction is key-based, so an exception
# message carrying a token or callback URL would reach the logs unredacted.
# Enable only where the data is not sensitive (e.g. the public demo).
_LOG_TRACEBACKS = config("DJANGO_LOG_TRACEBACKS", cast=bool, default=False)
_TRACEBACK_PROCESSORS = (
    [structlog.processors.format_exc_info] if _LOG_TRACEBACKS else []
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                redact_authentication_event,
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                *_TRACEBACK_PROCESSORS,
                structlog.processors.JSONRenderer(),
            ],
            "foreign_pre_chain": [
                redact_authentication_event,
                *_TRACEBACK_PROCESSORS,
            ],
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
