"""APScheduler wiring for `atlas.ingestion`'s periodic jobs.

Two jobs are registered against `django-apscheduler`'s DB-backed
`DjangoJobStore`: the manifest discovery run (`DISCOVERY_JOB_ID`) and the
API spec-URL refresh (`SPEC_REFRESH_JOB_ID` — conceptually `atlas.apis`'s
own concern, but scheduled here for now since this is where
the program's background-job runtime is introduced).
Job ids are plugin-owned so the plugin lifecycle machinery
can `pause_job`/`resume_job` them by id when `atlas.ingestion` is
disabled/re-enabled. `DjangoJobStore` persists job state in the database, so
a `pause_job`/`resume_job` call made from any process (e.g. the web process
handling a plugin-disable action) takes effect the next time the process
actually running this scheduler (the `ingestor` service, `runapscheduler`
command) wakes up — the two don't need to be the same process.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.conf import settings
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.util import close_old_connections

from .job_ids import DISCOVERY_JOB_ID, SPEC_REFRESH_JOB_ID

__all__ = [
    "DISCOVERY_JOB_ID",
    "SPEC_REFRESH_JOB_ID",
    "build_scheduler",
    "register_jobs",
]


def build_scheduler() -> BackgroundScheduler:
    """A scheduler wired to the shared DB-backed job store, no jobs yet."""
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    return scheduler


def register_jobs(scheduler: BackgroundScheduler) -> None:
    """Register the discovery-run and spec-refresh jobs on `interval`-second
    triggers.

    `close_old_connections` (django-apscheduler's own utility) wraps each
    job so a connection gone stale between runs in the scheduler's worker
    thread doesn't raise instead of transparently reconnecting.
    """
    from .pipeline import refresh_spec_urls, run_ingestion_pass

    interval = settings.INGESTOR_POLL_INTERVAL

    scheduler.add_job(
        close_old_connections(run_ingestion_pass),
        trigger=IntervalTrigger(seconds=interval),
        id=DISCOVERY_JOB_ID,
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        close_old_connections(refresh_spec_urls),
        trigger=IntervalTrigger(seconds=interval),
        id=SPEC_REFRESH_JOB_ID,
        replace_existing=True,
        max_instances=1,
    )
