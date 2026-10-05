## Context

Today the scheduler lives in the ingestion plugin: it builds an APScheduler `BackgroundScheduler` over `django-apscheduler`'s `DjangoJobStore`, registers two jobs, and exposes them through a `runapscheduler` command that the `ingestor` service runs. The plugin descriptor already carries `job_ids`, and the plugin runtime already pauses or resumes those ids by writing to the job store directly (no scheduler instance needed), so enablement is already decoupled from the scheduler process.

Two things tie scheduling to ingestion: the command and scheduler construction live in the ingestion package, and the `django_apscheduler` Django app only reaches `INSTALLED_APPS` through ingestion's own `django_apps`. A distribution that wants periodic work without ingestion has neither. The next feature (search indexing) is such a case.

The deployment already has one long-running process for jobs; the goal is to make it a platform capability, not to add infrastructure.

## Goals / Non-Goals

**Goals:**
- One scheduler process and one command owned by core, usable with any subset of plugins.
- A small, explicit contract for a plugin to contribute jobs, reusing the existing `job_ids` declaration and the existing pause/resume sync.
- Ingestion migrated to the contract with no behavioural change.
- Plugins can still ship a one-off management command and be deployed separately.

**Non-Goals:**
- New jobs, new intervals, or new settings.
- A task queue, retries, or distributed workers.
- Job administration UI.
- Running several scheduler processes concurrently (the DB job store gives no leader election; one process stays the rule).

## Decisions

### Decision 1: Hook named `register_jobs(scheduler)` beside `register_runtime()`

Core calls `register_jobs(scheduler)` on each active plugin's entry-point module, discovered the same way `register_runtime()` is (import the module named by the descriptor's `entry_point`, `getattr` the hook).

Alternatives considered:
- **Declarative job specs in the descriptor** (id, callable path, trigger). Static and inspectable, but the descriptor must stay importable before `django.setup()`, so callables would be dotted-path strings, and trigger objects would need a schema. More surface for no current need.
- **Plugin-run scheduler** (each plugin keeps its own command). That is today's shape; it multiplies processes and duplicates wiring.
- **Entry-point group `atlas.jobs`** separate from `atlas.plugins`. A second discovery mechanism for something already reachable from the plugin entry point.

The hook mirrors an existing pattern, needs no new discovery, and keeps scheduling code lazy (imports inside the hook, so a distribution without a plugin never imports it).

### Decision 2: Validate declared ids against registered ids

After each hook runs, core compares the job ids actually added to the scheduler with the descriptor's `job_ids`. An undeclared id fails startup naming the plugin. This keeps pause/resume by id trustworthy, since that mechanism only knows declared ids.

Alternatives: trust the plugin (silent drift, jobs that never pause on disable); register ids from the hook only (breaks the descriptor's role as the static contract used before Django setup).

### Decision 3: Scheduler construction and command move to core; app wiring becomes core-conditional

`build_scheduler()` and the command move into core. `django_apscheduler` is already a core dependency; the app is added to installed apps by core, unconditionally, instead of through the ingestion plugin's `django_apps`. Its migrations are small and apply everywhere.

Alternatives:
- **Add the app only when some selected plugin declares `job_ids`.** Avoids unused tables, but makes the schema depend on the selected plugin set, which complicates enabling a plugin later (migration timing). Unconditional is simpler and the cost is two tables.
- **Keep the app in ingestion and have core import it lazily.** Leaves the coupling that this change exists to remove.

### Decision 4: Keep the `ingestor` service and command name

The service and the `runapscheduler` command keep their names so existing compose files, Render config and operator muscle memory continue to work. Documentation renames the concept to "scheduler"; the compose service name can be renamed in a follow-up without a behaviour change.

Alternatives: rename the service now (breaking for anyone with overrides); add a second command alias (two names for one thing).

### Decision 5: Same single-process rule, no leader election

One scheduler process per deployment, as today. Documented as a constraint rather than solved. Scaling beyond one process would need a job-store lock, which is out of scope.

### Decision 6: Core provides an interval-job helper

Core exposes a helper that registers an interval job with the standard defaults (connection cleanup around the job body, a single running instance, replace-existing). Plugins use it by default and may call the scheduler directly for unusual triggers.

Alternatives: each plugin repeats the boilerplate (one forgotten connection cleanup shows up only as a failure hours later on a stale connection); the hook wraps every job automatically (hides behaviour and blocks plugins that need different settings).

### Decision 7: Core's schema stops referencing ingestion (claim moves into the plugin)

A distribution without ingestion could not migrate: `catalog.0001_initial` and `catalog.0012` depended on `ingestion` through `CatalogEntity.ingested_from`, a foreign key to `RegisteredRepository`. Core's schema must not depend on an optional plugin, and the pre-release status allows breaking history, so the dependency is removed rather than worked around.

- `CatalogEntity.ingested_from` is removed. Ingestion owns `EntityClaim` (one-to-one to the entity, `PROTECT` foreign key to the repository, reverse accessor `ingestion_claim`), so the dependency points ingestion → catalog. `source_kind` stays on the entity.
- `EntityService.create`/`update` lose their `ingested_from` parameter. Ingestion's upsert writes the claim in the same transaction right after the service call; core's adopt action does the same through `atlas_plugin_ingestion.claims` (lazy import, already guarded by `_ingestion_available()`).
- Reads go through `atlas_plugin_api.ingested_from()` (reads the reverse accessor, `None` when ingestion is absent) and `claim_relations()` for `select_related`, which is empty when ingestion is not installed. The API field `ingestedFrom` is unchanged.
- The composer no longer force-installs ingestion as a disabled plugin when a manifest omits it (`CORE_REQUIRED_PLUGIN_ID` removed).
- Migrations of `catalog`, `ingestion`, `apis` and `database-schema` are regenerated from scratch as a single `0001_initial` each, plus `catalog.0002_seed_catalog_home_settings` (the seed data migration). Historical-migration tests and the old backfill migrations are dropped. Existing development databases must be recreated.

- `atlas.database-schema` registered its facet-writer by importing `atlas_plugin_ingestion` unconditionally; it now skips registration when that package is not installed, so an image without ingestion starts cleanly.

Alternatives: a bare `ingested_from_id` integer without a foreign key (loses `PROTECT`, cascades and `ingested_from__...` joins); a claim model in core (keeps the dependency direction wrong).

## Risks / Trade-offs

- **A bad plugin hook crashes scheduler startup** → startup fails loudly naming the plugin; consistent with how runtime registration failures behave today, and a failing job body is isolated per job.
- **Unconditional `django_apscheduler` tables in distributions that never schedule** → two small tables; accepted for simpler migrations.
- **Mixed ordering with ingestion's one-off command** → the one-off command stays and calls the same job functions, so there is one implementation of each job body.
- **Regenerated migrations break existing databases** → accepted while pre-release; development databases are recreated, and the history restarts at `0001_initial`.
- **Documentation and examples refer to "ingestion scheduler"** → updated in the same change.

## Migration Plan

1. Add the core scheduler module, command and hook discovery; keep ingestion's old command working through a delegating shim for one step.
2. Move ingestion's registration to `register_jobs`; remove its scheduler module and old command; remove `django_apscheduler` from its `django_apps`.
3. Remove core's schema dependency on ingestion (Decision 7): move the claim into ingestion and regenerate migrations. Existing development databases must be recreated.
4. Update compose, Render config and docs wording.
5. Rollback: revert the change; job ids and the job store schema are unchanged, so persisted job rows remain valid in both directions. The regenerated migration history is not reversible in place: restore the previous databases or recreate them.

