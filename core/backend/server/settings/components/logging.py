import logging
import re
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

_UPLOAD_PATH = re.compile(r"(/api/uploads/)[^\s/?\"'<>]+")


class RedactUploadTokenFilter(logging.Filter):
    """Upload ticket tokens travel in the URL path, which Django's request
    and server loggers print verbatim (e.g. `Not Found: <path>`), so mask
    them before any handler formats the record."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if "/api/uploads/" in message:
            record.msg = _UPLOAD_PATH.sub(r"\1[REDACTED]", message)
            record.args = ()
        return True


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
    "filters": {
        "redact_upload_token": {"()": RedactUploadTokenFilter},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "filters": ["redact_upload_token"],
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    # Django's own loggers keep the handlers it built before this config
    # loaded, which print request paths unfiltered; route them through ours.
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


class LoggingContextVarsMiddleware:
    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        structlog.contextvars.clear_contextvars()
        return response
