"""The scheduler service's entrypoint (the `ingestor` Compose service).

Starts the platform scheduler against the DB-backed job store, registers
every active plugin's jobs (`apps.plugins.scheduler`), then blocks until the
process is signaled to stop. Available in every distribution; with no
job-contributing plugin it simply runs with no jobs.
"""

import signal
import time
from types import FrameType

from django.core.management.base import BaseCommand

from server.apps.plugins.resolver import load_selected_descriptors
from server.apps.plugins.scheduler import build_scheduler, register_plugin_jobs
from server.settings.selected_plugins import DISABLED_PLUGINS, SELECTED_PLUGINS


class Command(BaseCommand):
    help = "Run the scheduler for every active plugin's scheduled jobs."

    def handle(self, *args, **options) -> None:
        scheduler = build_scheduler()
        register_plugin_jobs(
            scheduler,
            load_selected_descriptors(SELECTED_PLUGINS),
            disabled_ids=DISABLED_PLUGINS,
        )
        scheduler.start()
        self.stdout.write(self.style.SUCCESS("Scheduler started"))

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
