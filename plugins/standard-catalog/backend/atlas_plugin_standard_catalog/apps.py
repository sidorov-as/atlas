from django.apps import AppConfig


class StandardCatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "atlas_plugin_standard_catalog"
    label = "standard_catalog"

    def ready(self) -> None:
        from . import signals  # noqa: F401

        # Kind registration happens in the shared "load selected runtime
        # entry points" phase (`PluginsConfig.ready()`), not here directly —
        # see `atlas_plugin_standard_catalog.plugin.register_runtime()`.
