from django.apps import AppConfig


class FlowsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "atlas_plugin_flows"
    label = "flows_plugin"

    def ready(self) -> None:
        # Permission registration happens in the shared "load selected runtime
        # entry points" phase (`PluginsConfig.ready()`), not here directly —
        # see `atlas_plugin_flows.plugin.register_runtime()`.
        pass
