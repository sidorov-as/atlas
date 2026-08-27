from django.apps import AppConfig


class C4Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "atlas_plugin_c4"
    label = "c4_plugin"

    def ready(self) -> None:
        # Permission registration happens in the shared "load selected runtime
        # entry points" phase (`PluginsConfig.ready()`), not here directly —
        # see `atlas_plugin_c4.plugin.register_runtime()`.
        pass
