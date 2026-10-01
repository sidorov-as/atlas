from django.apps import AppConfig


class McpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "atlas_plugin_mcp"
    label = "mcp_plugin"

    def ready(self) -> None:
        # This plugin registers no runtime permissions/purge scanners/jobs of
        # its own — everything it exposes reads/writes through
        # `EntityService`/`FlowService`, whose own permission checks already
        # ran when *they* registered. Nothing to do here; see
        # `atlas_plugin_mcp.plugin.register_runtime()`.
        pass
