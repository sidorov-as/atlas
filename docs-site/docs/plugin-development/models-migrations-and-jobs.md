---
title: Models, migrations, and jobs
description: Keep plugin-owned data removable, migrations safe, and scheduled work aligned with plugin lifecycle.
audience: [plugin-author]
page-type: guide
---

# Models, migrations, and jobs

A plugin owns its own Django app, models, migrations, and background-job
identifiers. It may depend on Core and its own migration history, never on a
sibling plugin's migrations or private models.

## Model and migration boundary

Put persistent data in a plugin Django app named in `PluginDescriptor.django_apps`.
Reference Core through public contracts or stable identifiers; do not make a
migration dependency on another plugin. Prefer additive, expand-contract
changes. Add a nullable field or table, deploy code that tolerates both shapes,
backfill separately, then make a contracted change only after reviewing its
operational impact.

Run the repository checks before proposing a destructive operation:

```shell
cd core/backend
uv run django-safe-migrations
uv run python manage.py check_migration_boundaries
```

The latter reports the app, migration, and conflicting plugin ownership. A
suppression for the migration safety linter needs an explicit, reviewed
`# safe-migrations: ignore ...` comment. It does not replace a backup or
deployment plan. See [data safety](../operating-atlas/data-safety.md).

## Register scheduled work

Atlas Core owns one scheduler process for the whole distribution: the
`runapscheduler` management command (the `ingestor` service in the Compose
files), backed by the `django-apscheduler` job store. A plugin does not run its
own scheduler. It contributes jobs in two steps.

1. Declare every job id on the descriptor.
2. Expose a module-level `register_jobs(scheduler)` hook on the entry-point
   module (the module named by `entry_point`, next to `register_runtime()`).

```python
PLUGIN = PluginDescriptor(
    id="atlas.inventory",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("atlas_plugin_inventory",),
    entry_point="atlas_plugin_inventory.plugin:PLUGIN",
    job_ids=("atlas.inventory.refresh",),
)


def register_jobs(scheduler) -> None:
    from atlas_plugin_api import add_interval_job

    from .jobs import refresh_inventory

    add_interval_job(
        scheduler, refresh_inventory, job_id="atlas.inventory.refresh", seconds=300
    )
```

When the scheduler starts, Core calls the hook once for every selected plugin
that is not disabled. A plugin without the hook is skipped, and a disabled
plugin's hook is not called. Importing the plugin module must not register or
start anything; keep imports of job bodies and `django_apscheduler` inside the
hook so a distribution without the plugin never imports them.

`add_interval_job` applies the platform defaults: the job body is wrapped in
`close_old_connections`, only one instance runs at a time (an overlapping
trigger is skipped), and a persisted job with the same id is replaced. For a
different trigger, call `scheduler.add_job` directly; the id must still be
declared on the descriptor.

If the hook registers an id the descriptor does not declare, scheduler startup
fails and names the plugin and the id. This keeps pause and resume by id
trustworthy: Atlas pauses declared jobs while the plugin is disabled and
resumes them when it is active, by writing to the job store, so it works
regardless of which process changes the state. Startup tolerates a job that is
not yet present in a fresh job store.

Run exactly one scheduler process per deployment. The job store has no leader
election, so a second `runapscheduler` would run every job twice. The
scheduler also starts, with no jobs, in a distribution where no selected plugin
contributes any.

Jobs must be idempotent, tolerate an unavailable dependency, and avoid writing
data after their plugin is disabled. A job that raises is logged and does not
stop other jobs. Treat disablement and removal as data-preserving states; only
an operator's explicit purge deletes scoped model rows. See
[plugin lifecycle](../operating-atlas/plugin-lifecycle.md).

### Run a plugin's work as a separate deployment

The shared scheduler is the default, not a requirement. A plugin may also ship
a management command that performs its work once, built on the same job
function the hook registers, so there is one implementation. Ingestion does
this with `manage.py ingest`. An operator can run such a command from cron, a
Kubernetes `CronJob`, or a dedicated container, with or without
`runapscheduler` running. If both run, the job body must tolerate overlapping
executions.

## Verify lifecycle safety

Test model behavior, migration paths, job registration, failure isolation, and
disabled-job pause/resume. Do not put a sibling plugin's ORM access in a model
method or migration. Continue with [testing plugins](testing.md) and
[backend collaboration](backend-collaboration.md).
