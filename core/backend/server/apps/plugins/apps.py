from django.apps import AppConfig


class PluginsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "server.apps.plugins"
    label = "plugins"

    def ready(self) -> None:
        # Deferred: composition validation transitively imports Django
        # models (via the Entity Kind registry), so it must not run until
        # django.setup() has finished loading every app's models.
        from server.settings.selected_plugins import (
            DISABLED_PLUGINS,
            SELECTED_PLUGINS,
        )

        from .composition import validate_composition
        from .resolver import load_selected_descriptors

        validate_composition(
            load_selected_descriptors(SELECTED_PLUGINS),
            disabled_ids=DISABLED_PLUGINS,
        )
