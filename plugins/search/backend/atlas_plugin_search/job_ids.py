"""`atlas.search`'s `django-apscheduler` job ids.

Kept apart from `plugin.py`'s runtime hooks so the static descriptor module
(imported before `django.setup()`) can declare them on
`PluginDescriptor.job_ids` without importing scheduler or Django code.
"""

DRAIN_JOB_ID = "atlas.search.drain"
REBUILD_JOB_ID = "atlas.search.rebuild"
INITIAL_REBUILD_JOB_ID = "atlas.search.initial_rebuild"
