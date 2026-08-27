__all__ = ["register_standard_catalog_kinds"]


def register_standard_catalog_kinds(*, owner: str | None = None) -> None:
    """Register System/Component/Resource/Group/Actor — the Standard Catalog kinds.

    Called from `atlas_plugin_standard_catalog.plugin.register_runtime()`
    during the shared runtime entry-point-loading phase
    (`server.apps.plugins.runtime`), itself invoked from `PluginsConfig.ready()`
    — after `django.setup()`.
    """
    from atlas_plugin_api import register_kind

    from .actor_handler import ActorKindHandler
    from .component_handler import ComponentKindHandler
    from .group_handler import GroupKindHandler
    from .resource_handler import ResourceKindHandler
    from .system_handler import SystemKindHandler

    handler_classes = (
        SystemKindHandler,
        ComponentKindHandler,
        ResourceKindHandler,
        GroupKindHandler,
        ActorKindHandler,
    )
    for handler_cls in handler_classes:
        register_kind(handler_cls(), owner=owner)

    _register_api_delete_guard(owner=owner)
    _register_purge_scanner(owner=owner)


def _register_api_delete_guard(*, owner: str | None) -> None:
    """Register Component's "does this API still have referencing Components?"
    check against `atlas_plugin_apis`'s delete-guard extension point

    `atlas.apis` is optional (its own `plugin.py` docstring) — this plugin
    (`atlas.standard-catalog`) is required and always registers its kinds,
    so importing `atlas_plugin_apis` unconditionally here would crash a
    distribution that omits it. Guarded the same way
    `server.apps.catalog.api.helpers._ingestion_available()` guards its own
    optional-plugin import, for the same reason.
    """
    from django.apps import apps as django_apps

    if not django_apps.is_installed("atlas_plugin_apis"):
        return

    from atlas_plugin_apis.extension_points import register_delete_guard

    from .component_handler import check_component_references_api

    register_delete_guard(
        owner or "atlas.standard-catalog", check_component_references_api
    )


def _register_purge_scanner(*, owner: str | None) -> None:
    """Register this plugin's Purge reference scan against `atlas_plugin_api.purge`
    — combines both of this
    plugin's checks (`ComponentDetails.depends_on` for a Resource,
    `provides_apis`/`consumes_apis` for an API) into one scanner, since the
    registry holds at most one per registering plugin id (unlike the API
    delete-guard registry above, no optional-plugin guard is needed: both
    checks live on this plugin's own `ComponentDetails` model, always installed.
    """
    from atlas_plugin_api import register_purge_scanner

    from .component_handler import check_api_purge_references
    from .resource_handler import check_resource_purge_references

    def _scan(entity):
        return [
            *check_resource_purge_references(entity),
            *check_api_purge_references(entity),
        ]

    register_purge_scanner(owner or "atlas.standard-catalog", _scan)
