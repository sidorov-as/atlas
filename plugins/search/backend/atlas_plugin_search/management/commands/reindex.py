"""Build the complete search index without a scheduler.

For images and deployments that ship a ready index: run it after the catalog
is seeded. It is the same rebuild the scheduled job runs.
"""

from django.core.management.base import BaseCommand, CommandError

from atlas_plugin_search import indexer, runtime


class Command(BaseCommand):
    help = "Rebuild the whole search index from every registered source."

    def handle(self, *args, **options) -> None:
        if not runtime.is_active():
            raise CommandError(
                "Search is not active: the atlas.search plugin is not selected "
                "or is disabled"
            )
        try:
            count = indexer.rebuild_index()
        except indexer.IndexingBusyError as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            raise CommandError(f"Rebuild failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Indexed {count} documents"))
