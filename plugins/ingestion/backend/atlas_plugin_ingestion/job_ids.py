"""`atlas.ingestion`'s `django-apscheduler` job ids.

Kept apart from `plugin.py`'s runtime hooks so the static descriptor module
(imported before `django.setup()` to compute `INSTALLED_APPS`) declares
them on `PluginDescriptor.job_ids` without importing scheduler or Django
code; `register_jobs()` in `plugin.py` registers them.
"""

DISCOVERY_JOB_ID = "atlas.ingestion.discovery"
SPEC_REFRESH_JOB_ID = "atlas.ingestion.spec_refresh"
