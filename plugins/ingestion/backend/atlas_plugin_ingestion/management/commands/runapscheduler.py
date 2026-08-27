"""The `ingestor` Compose service's entrypoint.

Starts the shared APScheduler `BackgroundScheduler` against the DB-backed
job store, registers `atlas.ingestion`'s discovery-run and spec-refresh jobs
under their plugin-owned ids (`scheduler.py`), then blocks until the process
is signaled to stop — replaces the old hand-rolled poll loop. `manage.py
ingest --once` remains for a single manual/test pass without a scheduler.
"""

import signal
import time
from types import FrameType

from django.core.management.base import BaseCommand

from atlas_plugin_ingestion.scheduler import build_scheduler, register_jobs


class Command(BaseCommand):
    help = "Run atlas.ingestion's scheduled jobs (discovery, spec refresh)."

    def handle(self, *args, **options) -> None:
        scheduler = build_scheduler()
        register_jobs(scheduler)
        scheduler.start()
        self.stdout.write(self.style.SUCCESS("Ingestion scheduler started"))

        stop_requested = False

        def _request_stop(signum: int, frame: FrameType | None) -> None:
            nonlocal stop_requested
            stop_requested = True

        signal.signal(signal.SIGINT, _request_stop)
        signal.signal(signal.SIGTERM, _request_stop)

        try:
            while not stop_requested:
                time.sleep(1)
        finally:
            scheduler.shutdown()
