from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "server.apps.catalog"
    label = "catalog"

    def ready(self) -> None:
        # Kind registration happens in the shared "load selected runtime
        # entry points" phase (`PluginsConfig.ready()`), not here directly —
        # see `server.apps.catalog.plugin.register_runtime()`. Core session
        # metadata signals remain local to the catalog app; provider-specific
        # claims are returned through the public provisioning contract.
        from server.apps.catalog import auth_signals  # noqa: F401
