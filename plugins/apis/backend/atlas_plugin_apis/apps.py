from django.apps import AppConfig


class ApisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "atlas_plugin_apis"
    label = "apis_plugin"

    def ready(self) -> None:
        from . import signals  # noqa: F401

        # Kind registration happens in the shared "load selected runtime
        # entry points" phase (`PluginsConfig.ready()`), not here directly —
        # see `atlas_plugin_apis.plugin.register_runtime()`.
