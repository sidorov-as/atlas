import logging

from django.core.exceptions import ImproperlyConfigured
from django.core.mail.handler import DEFAULT_MAILER_ALIAS

from server.settings.components import config

logger = logging.getLogger(__name__)

DEBUG = False
ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS", cast=lambda value: value.split(",")
)
SECURE_SSL_REDIRECT = config(
    "DJANGO_SECURE_SSL_REDIRECT", cast=bool, default=True
)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# The `unsafe-development-secret`/`change-me` fallbacks in `common.py` and
# `.env.example` are only safe for local development. Production must never
# be reachable with a missing, example, or low-entropy secret key (prerelease
# security audit finding).
_SECRET_KEY_PLACEHOLDERS = frozenset({"unsafe-development-secret", "change-me"})
_SECRET_KEY_MINIMUM_LENGTH = 50
if SECRET_KEY in _SECRET_KEY_PLACEHOLDERS:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is missing or set to a known example value "
        f"({SECRET_KEY!r}). Set DJANGO_SECRET_KEY to a unique, random value "
        "before running in production."
    )
if len(SECRET_KEY) < _SECRET_KEY_MINIMUM_LENGTH:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is too short for production (must be at least "
        f"{_SECRET_KEY_MINIMUM_LENGTH} characters, got {len(SECRET_KEY)})."
    )

# `common.py`'s MAILERS default (`locmem`) silently discards mail everywhere
# it's used, including allauth's password-recovery email. In production,
# discarding a recovery email is worse than not offering recovery at all, so
# disable it via the same policy gate `auth_middleware` already enforces
# (`auth_policy.public_recovery_enabled()`) rather than shipping a feature
# that looks like it works but never delivers its email.
if MAILERS.get(DEFAULT_MAILER_ALIAS, {}).get("BACKEND") == (
    "django.core.mail.backends.locmem.EmailBackend"
):
    logger.warning(
        "No real mail backend is configured for production (MAILERS[%r] "
        "still resolves to locmem); disabling password-recovery until a "
        "real mailer is set.",
        DEFAULT_MAILER_ALIAS,
    )
    ATLAS_AUTHENTICATION = {
        **ATLAS_AUTHENTICATION,
        "recovery": {
            **ATLAS_AUTHENTICATION.get("recovery", {}),
            "mode": "disabled",
        },
    }
