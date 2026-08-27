from csp.constants import SELF

from server.settings.components import config
from server.settings.components.common import INSTALLED_APPS
from server.settings.components.csp import CONTENT_SECURITY_POLICY

DEBUG = config("DJANGO_DEBUG", cast=bool, default=True)
ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    cast=lambda value: value.split(","),
    default="localhost,127.0.0.1,0.0.0.0",
)
CONTENT_SECURITY_POLICY["DIRECTIVES"]["connect-src"].extend(
    [SELF, "http://localhost:5173"]
)
INSTALLED_APPS += ("django_migration_linter", "django_safe_migrations")

# A destructive migration must be
# blocked by CI unless explicitly marked maintenance-mode. SM002/SM003 ship as
# WARNING severity upstream; promoting them to build-failing here is what
# actually enforces the "blocked outside maintenance mode" requirement — an
# author opts a specific operation out with an inline
# `# safe-migrations: ignore SM002 -- <reason>` comment (django-safe-migrations'
# own suppression convention), which is exactly the "marker ... with a required
# justification comment" the lint requires. SM020 (AlterField narrowing
# nullability) already defaults to ERROR severity upstream, so it's already
# blocking without being listed here.
SAFE_MIGRATIONS = {
    "WARNINGS_AS_ERRORS": ["SM002", "SM003"],
    "EXCLUDED_APPS": [
        "admin",
        "auth",
        "contenttypes",
        "sessions",
        "messages",
        "staticfiles",
        "postgres",
        "sites",
        "allauth",
        "account",
        "headless",
        "socialaccount",
        "openid_connect",
        "dmr",
        "corsheaders",
        "axes",
        "health_check",
        "django_apscheduler",
        "django_migration_linter",
        "django_safe_migrations",
    ],
}
