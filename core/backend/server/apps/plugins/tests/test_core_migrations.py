"""Core's migration history must not depend on an optional plugin."""

from django.db.migrations.loader import MigrationLoader

# Plugin Django app labels core must never depend on: a distribution that
# doesn't select the plugin couldn't migrate if core's history required them.
OPTIONAL_PLUGIN_APP_LABELS = {"ingestion"}


def test_catalog_migrations_do_not_depend_on_optional_plugins():
    loader = MigrationLoader(None, load=False)
    loader.load_disk()  # reads migration files only; no database needed

    offenders = sorted(
        f"catalog.{name} -> {dep_app}.{dep_name}"
        for (app, name), migration in loader.disk_migrations.items()
        if app == "catalog"
        for dep_app, dep_name in migration.dependencies
        if dep_app in OPTIONAL_PLUGIN_APP_LABELS
    )

    assert offenders == []
