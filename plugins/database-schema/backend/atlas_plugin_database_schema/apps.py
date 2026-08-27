from django.apps import AppConfig


class DatabaseSchemaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "atlas_plugin_database_schema"
    label = "database_schema_plugin"

    def ready(self) -> None:
        # This plugin registers nothing at runtime yet (no capability or
        # permission of its own — `schema.host.v1` is declared by the
        # Standard Catalog plugin's `resource` kind, not by this plugin);
        # see `atlas_plugin_database_schema.plugin`.
        pass
