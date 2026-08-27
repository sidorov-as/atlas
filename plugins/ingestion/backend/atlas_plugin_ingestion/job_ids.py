"""`atlas.ingestion`'s `django-apscheduler` job ids.

Split out of `scheduler.py` so `plugin.py` (the static descriptor module,
imported before `django.setup()` to compute `INSTALLED_APPS`) can declare
them on `PluginDescriptor.job_ids` without importing `scheduler.py` —
`scheduler.py` pulls in `django_apscheduler.jobstores`, which imports
Django models at module level and would raise before the app registry is
ready.
"""

DISCOVERY_JOB_ID = "atlas.ingestion.discovery"
SPEC_REFRESH_JOB_ID = "atlas.ingestion.spec_refresh"
