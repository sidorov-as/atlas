from django.apps import AppConfig


class SearchPostgresConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "atlas_plugin_search_postgres"
    label = "search_postgres"
