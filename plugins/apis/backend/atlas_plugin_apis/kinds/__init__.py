__all__ = ["register_apis_kinds"]


def register_apis_kinds(*, owner: str | None = None) -> None:
    """Register `api` — split out of `server.apps.catalog.kinds.register_default_kinds`

    Called from `atlas_plugin_apis.plugin.register_runtime()` during the
    shared runtime entry-point-loading phase (`server.apps.plugins.runtime`),
    itself invoked from `PluginsConfig.ready()` — after `django.setup()`.
    """
    from atlas_plugin_api import register_kind

    from .api_handler import ApiKindHandler

    register_kind(ApiKindHandler(), owner=owner)
