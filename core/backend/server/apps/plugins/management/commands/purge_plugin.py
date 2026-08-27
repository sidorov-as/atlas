"""`manage.py purge_plugin <plugin_id>`.

Purge is deliberately separate from `disabled`/removal: neither of those
deletes data (ADR 0008), so an operator who actually wants a plugin's data
gone has to say so explicitly, here. Requires the plugin's code to still be
selected (`SELECTED_PLUGINS`) — its models are how scope is computed, so a
plugin whose code is already gone can't be purged
(plugin-architecture.md:589).

Defaults to a dry run reporting the exact tables/row counts that would be
deleted; only `--confirm` actually deletes, inside one transaction so a
failure partway through leaves nothing partially purged.

Scope is every model in the plugin descriptor's own `django_apps` — for the
acceptance case (`atlas.database-schema`), that's exactly the
`DatabaseSchema` Facet table, `OneToOneField`-attached to `CatalogEntity`
but not the other way round, so deleting it never touches the
`Resource`/`CatalogEntity` row it was attached to.
"""

from django.apps import apps as django_apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from server.apps.plugins.resolver import load_selected_descriptors
from server.settings.selected_plugins import SELECTED_PLUGINS


class Command(BaseCommand):
    help = (
        "Report (default) or delete a plugin's data. Dry run by default; "
        "pass --confirm to actually delete. Requires the plugin to still "
        "be selected, since scope is computed from its models."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "plugin_id",
            help="Plugin id to purge, e.g. 'atlas.database-schema'.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help=(
                "Actually delete the reported rows. Without this, only "
                "scope is reported."
            ),
        )

    def handle(self, *args, **options) -> None:
        plugin_id = options["plugin_id"]
        models = _scoped_models(_resolve_descriptor(plugin_id))

        scope = [(model, model._default_manager.count()) for model in models]
        self._report_scope(plugin_id, scope)

        if not options["confirm"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Dry run only — no rows deleted. "
                    "Re-run with --confirm to purge.",
                )
            )
            return

        with transaction.atomic():
            for model, _count in scope:
                model._default_manager.all().delete()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Purged {plugin_id!r}."))

    def _report_scope(self, plugin_id: str, scope: list) -> None:
        self.stdout.write(f"Purge scope for {plugin_id!r}:")
        if not scope:
            self.stdout.write("  (no models — nothing to delete)")
            return
        for model, count in scope:
            self.stdout.write(f"  {model._meta.db_table}: {count} row(s)")


def _resolve_descriptor(plugin_id: str):
    for descriptor in load_selected_descriptors(SELECTED_PLUGINS):
        if descriptor.id == plugin_id:
            return descriptor
    raise CommandError(
        f"{plugin_id!r} is not among the selected plugins — its code must "
        "still be installed (selected in the manifest) to compute purge "
        "scope.",
    )


def _scoped_models(descriptor) -> list:
    configs_by_name = {
        config.name: config for config in django_apps.get_app_configs()
    }
    models = []
    for app_name in descriptor.django_apps:
        app_config = configs_by_name.get(app_name)
        if app_config is not None:
            models.extend(app_config.get_models())
    return models
