import warnings
from pathlib import Path

from django.utils.translation import gettext_lazy as _

from server.apps.plugins import (
    load_selected_descriptors,
    resolve_installed_apps,
    verify_selected_descriptors,
)
from server.apps.plugins.config import registry as _plugin_config_registry
from server.settings import selected_plugins as _selected_plugins
from server.settings.components import BASE_DIR, config

AUTHENTICATION = _selected_plugins.AUTHENTICATION
SELECTED_PLUGINS = _selected_plugins.SELECTED_PLUGINS
PLUGIN_CONFIGS = getattr(_selected_plugins, "PLUGIN_CONFIGS", {})

SECRET_KEY = config("DJANGO_SECRET_KEY", default="unsafe-development-secret")
DEBUG = config("DJANGO_DEBUG", cast=bool, default=False)
ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS", cast=lambda value: value.split(","), default=""
)
CSRF_TRUSTED_ORIGINS = config(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    cast=lambda value: value.split(","),
    default="http://localhost:5173",
)

# Transitional environment projection for the namespaced OIDC plugin config.
# New deployments use the manifest fields `discoveryUrl` and
# `expectedIssuer`. `OIDC_ISSUER` previously meant the discovery document URL,
# so it is accepted only as that field and never silently trusted as issuer.
# Runs before the static phase below so a runnable example's disposable,
# runtime-generated credentials take priority over whatever placeholder its
# manifest-derived PLUGIN_CONFIGS declares for the same plugin id.
_oidc_discovery_url = config("OIDC_DISCOVERY_URL", default="")
_legacy_oidc_discovery_url = config("OIDC_ISSUER", default="")
if not _oidc_discovery_url and _legacy_oidc_discovery_url:
    warnings.warn(
        "OIDC_ISSUER is deprecated and represented a discovery URL; rename it "
        "to OIDC_DISCOVERY_URL and set OIDC_EXPECTED_ISSUER explicitly.",
        DeprecationWarning,
        stacklevel=2,
    )
    _oidc_discovery_url = _legacy_oidc_discovery_url
_oidc_expected_issuer = config("OIDC_EXPECTED_ISSUER", default="")
_oidc_client_id = config("OIDC_CLIENT_ID", default="")

if any((_oidc_discovery_url, _oidc_expected_issuer, _oidc_client_id)):
    from django.core.exceptions import ImproperlyConfigured

    if not all((_oidc_discovery_url, _oidc_expected_issuer, _oidc_client_id)):
        raise ImproperlyConfigured(
            "OIDC requires OIDC_DISCOVERY_URL, OIDC_EXPECTED_ISSUER, and "
            "OIDC_CLIENT_ID. OIDC_ISSUER is a deprecated discovery-URL alias "
            "and cannot establish the expected issuer by itself."
        )
    from atlas_plugin_api import SecretRef
    from atlas_plugin_auth_oidc.config import OIDCConfig
    from atlas_plugin_auth_oidc.plugin import PROVIDER_ID as OIDC_PROVIDER_ID

    _plugin_config_registry.register(
        OIDC_PROVIDER_ID,
        OIDCConfig,
        {
            "discoveryUrl": _oidc_discovery_url,
            "expectedIssuer": _oidc_expected_issuer,
            "clientId": _oidc_client_id,
            "clientSecret": SecretRef(from_env="OIDC_CLIENT_SECRET"),
            "scopes": config(
                "OIDC_SCOPES",
                cast=lambda value: tuple(
                    item for item in value.split() if item
                ),
                default="openid profile email",
            ),
            "groupsClaim": config("OIDC_GROUPS_CLAIM", default="groups"),
            "allowedDestinations": config(
                "OIDC_ALLOWED_DESTINATIONS",
                cast=lambda value: tuple(
                    item.strip() for item in value.split(",") if item.strip()
                ),
                default="",
            ),
            "allowDevelopmentHttp": config(
                "OIDC_ALLOW_DEVELOPMENT_HTTP",
                cast=bool,
                default=False,
            ),
        },
    )

# Transitional environment projection for the namespaced Gitea plugin config.
# The runnable example creates its disposable OAuth application at startup and
# exports the generated client id/secret only inside a shared runtime volume.
_gitea_instance_origin = config("GITEA_INSTANCE_ORIGIN", default="")
_gitea_client_id = config("GITEA_CLIENT_ID", default="")

if any((_gitea_instance_origin, _gitea_client_id)):
    from django.core.exceptions import ImproperlyConfigured

    if not all((_gitea_instance_origin, _gitea_client_id)):
        raise ImproperlyConfigured(
            "Gitea requires GITEA_INSTANCE_ORIGIN and GITEA_CLIENT_ID."
        )
    from atlas_plugin_api import SecretRef
    from atlas_plugin_auth_gitea.config import GiteaConfig
    from atlas_plugin_auth_gitea.plugin import (
        PROVIDER_ID as GITEA_PROVIDER_ID,
    )

    _plugin_config_registry.register(
        GITEA_PROVIDER_ID,
        GiteaConfig,
        {
            "instanceOrigin": _gitea_instance_origin,
            "clientId": _gitea_client_id,
            "clientSecret": SecretRef(from_env="GITEA_CLIENT_SECRET"),
            "scopes": ["read:user"],
            "oauthPkceEnabled": True,
            "allowedDestinations": config(
                "GITEA_ALLOWED_DESTINATIONS",
                cast=lambda value: tuple(
                    item.strip() for item in value.split(",") if item.strip()
                ),
                default="",
            ),
            "allowDevelopmentHttp": config(
                "GITEA_ALLOW_DEVELOPMENT_HTTP",
                cast=bool,
                default=False,
            ),
        },
    )

# Static phase (plugin-architecture.md:390-394): read → verify → generate
# INSTALLED_APPS, all before `django.setup()` — which is about to run as
# soon as this settings module finishes importing.
_selected_descriptors = load_selected_descriptors(SELECTED_PLUGINS)
verify_selected_descriptors(_selected_descriptors)
for _descriptor in _selected_descriptors:
    if _plugin_config_registry.get(_descriptor.id) is not None:
        # Already bound above by an environment projection (a runnable
        # example's disposable, runtime-generated credentials) — the
        # manifest-derived PLUGIN_CONFIGS placeholder for this id must not
        # overwrite it.
        continue
    _raw_plugin_config = PLUGIN_CONFIGS.get(_descriptor.id)
    if _raw_plugin_config is not None and _descriptor.config_schema is not None:
        _plugin_config_registry.register(
            _descriptor.id,
            _descriptor.config_schema,
            _raw_plugin_config,
        )

INSTALLED_APPS = resolve_installed_apps(
    _selected_descriptors,
    additional_apps=(
        # Core infrastructure, not itself an operator-selectable plugin —
        # its `ready()` runs the shared runtime entry-point-loading phase
        # and composition validation for the selected plugins above.
        "server.apps.plugins",
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.postgres",
        "django.contrib.sites",
        "django.contrib.staticfiles",
        "allauth",
        "allauth.account",
        "allauth.headless",
        "allauth.socialaccount",
        "allauth.socialaccount.providers.gitea",
        "allauth.socialaccount.providers.openid_connect",
        "dmr",
        "corsheaders",
        "axes",
        "health_check",
        # The scheduler's job store (`runapscheduler`): core-owned and
        # unconditional, so any selected plugin can contribute jobs and
        # migrations don't depend on the plugin set.
        "django_apscheduler",
    ),
)

MIDDLEWARE = (
    "corsheaders.middleware.CorsMiddleware",
    "server.settings.components.logging.LoggingContextVarsMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django_permissions_policy.PermissionsPolicyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "server.apps.catalog.auth_middleware.AuthenticationPolicyMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
)

ROOT_URLCONF = "server.urls"
WSGI_APPLICATION = "server.wsgi.application"
ASGI_APPLICATION = "server.asgi.application"
SITE_ID = 1
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
LANGUAGES = (("en", _("English")),)
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = Path(
    config("DJANGO_STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="atlas"),
        "USER": config("POSTGRES_USER", default="atlas"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="atlas"),
        # Only the template-aligned variables are authoritative.  This avoids
        # inheriting a stale POSTGRES_PORT from a pre-migration local .env.
        "HOST": config("DJANGO_DATABASE_HOST", default="localhost"),
        "PORT": config("DJANGO_DATABASE_PORT", cast=int, default=5432),
        "CONN_MAX_AGE": config("CONN_MAX_AGE", cast=int, default=60),
    },
}

AUTHENTICATION_BACKENDS = (
    "axes.backends.AxesBackend",
    "server.apps.catalog.auth_backends.AtlasModelBackend",
    "server.apps.catalog.auth_backends.AtlasAllauthAuthenticationBackend",
)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
ATLAS_AUTHENTICATION = AUTHENTICATION
_password_policy = AUTHENTICATION.get("passwordPolicy", {})
ATLAS_PASSWORD_MAXIMUM_LENGTH = _password_policy.get("maximumLength", 128)
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.MinimumLengthValidator"
        ),
        "OPTIONS": {"min_length": _password_policy.get("minimumLength", 15)},
    },
    {
        "NAME": (
            "server.apps.catalog.password_validation.MaximumLengthValidator"
        ),
        "OPTIONS": {"max_length": ATLAS_PASSWORD_MAXIMUM_LENGTH},
    },
]
if _password_policy.get("rejectCommon", True):
    AUTH_PASSWORD_VALIDATORS.append(
        {
            "NAME": (
                "django.contrib.auth.password_validation."
                "CommonPasswordValidator"
            ),
        }
    )
if _password_policy.get("rejectUserSimilarity", True):
    AUTH_PASSWORD_VALIDATORS.append(
        {
            "NAME": (
                "django.contrib.auth.password_validation."
                "UserAttributeSimilarityValidator"
            ),
        }
    )
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

CORS_ALLOWED_ORIGINS = config(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    cast=lambda value: value.split(","),
    default="http://localhost:5173",
)
CORS_ALLOW_CREDENTIALS = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
# The browser SPA reads this cookie to send Django's double-submit CSRF header.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
PERMISSIONS_POLICY = {}
MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    },
}
INGESTOR_POLL_INTERVAL = config("INGESTOR_POLL_INTERVAL", cast=int, default=60)

# Hosts exempted from the HTTPS-only / non-reserved-address requirement when
# resolving an API's `spec_url` (HTTPS-only by
# default, operator allowlist for exceptions) — e.g. an internal Git or
# artifact server intentionally reachable only over HTTP or a private
# address. Empty (deny) by default.
ATLAS_APIS_SPEC_URL_ALLOWLIST = config(
    "ATLAS_APIS_SPEC_URL_ALLOWLIST",
    cast=lambda value: [
        host.strip() for host in value.split(",") if host.strip()
    ],
    default="",
)

ACCOUNT_LOGIN_METHODS = {"username"}
ACCOUNT_SIGNUP_FIELDS = ["username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_UNIQUE_EMAIL = False
SOCIALACCOUNT_STORE_TOKENS = False
HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("browser",)
HEADLESS_FRONTEND_URLS = {
    "account_signup": "/login",
    "account_reset_password_from_key": "/reset-password/{key}",
}
ACCOUNT_ADAPTER = "server.apps.catalog.account_adapter.AtlasAccountAdapter"
PASSWORD_RESET_TIMEOUT = AUTHENTICATION.get("recovery", {}).get(
    "tokenMaxAgeSeconds",
    3600,
)
