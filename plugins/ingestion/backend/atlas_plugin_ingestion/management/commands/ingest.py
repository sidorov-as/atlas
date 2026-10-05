"""A single manual/test ingestion pass.

Periodic scheduling lives in core's `runapscheduler` now —
this command only runs one pass and exits, for local development or a
one-off manual trigger.
"""

from django.core.management.base import BaseCommand

from atlas_plugin_ingestion.pipeline import (
    refresh_spec_urls,
    run_ingestion_pass,
)


class Command(BaseCommand):
    help = "Run a single ingestion pass against every registered repository."

    def handle(self, *args, **options) -> None:
        run_ingestion_pass()
        refresh_spec_urls()
