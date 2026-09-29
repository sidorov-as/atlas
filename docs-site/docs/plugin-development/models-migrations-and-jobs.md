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
poetry run django-safe-migrations
poetry run python manage.py check_migration_boundaries
```

The latter reports the app, migration, and conflicting plugin ownership. A
suppression for the migration safety linter needs an explicit, reviewed
`# safe-migrations: ignore ...` comment. It does not replace a backup or
deployment plan. See [data safety](../operating-atlas/data-safety.md).

## Register scheduled work

Declare every `django-apscheduler` job id on the descriptor. Register the job
from the plugin's runtime path after Django setup. Atlas pauses declared jobs
while the plugin is disabled and resumes them when it is active. Startup
tolerates a job that is not yet present in a fresh job store.

```python
PLUGIN = PluginDescriptor(
    id="atlas.inventory",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("atlas_plugin_inventory",),
    entry_point="atlas_plugin_inventory.plugin:PLUGIN",
    job_ids=("atlas.inventory.refresh",),
)
```

Jobs must be idempotent, tolerate an unavailable dependency, and avoid writing
data after their plugin is disabled. Treat disablement and removal as
data-preserving states; only an operator's explicit purge deletes scoped model
rows. See [plugin lifecycle](../operating-atlas/plugin-lifecycle.md).

## Verify lifecycle safety

Test model behavior, migration paths, job registration, failure isolation, and
disabled-job pause/resume. Do not put a sibling plugin's ORM access in a model
method or migration. Continue with [testing plugins](testing.md) and
[backend collaboration](backend-collaboration.md).
