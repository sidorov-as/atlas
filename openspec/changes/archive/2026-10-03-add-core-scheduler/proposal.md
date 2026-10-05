## Why

Background jobs are currently owned by the ingestion plugin: the `runapscheduler` command, the scheduler construction and the `django_apscheduler` app all live in `atlas.ingestion`. Any other plugin that needs periodic work (search indexing is the next one) would have to depend on ingestion or run a second, parallel scheduler. Scheduling is a platform concern, not an ingestion concern.

## What Changes

- Core owns the scheduler: a single `runapscheduler` command and one scheduler process for the whole distribution, backed by the existing DB job store.
- A plugin contributes jobs through a declared hook instead of owning the scheduler; the core discovers the hook on every active plugin when the scheduler starts.
- Job ids declared by a plugin keep being paused when the plugin is disabled and resumed when it is active, unchanged from today.
- `atlas.ingestion` stops owning the scheduler and contributes its discovery and spec-refresh jobs through the new hook. Its one-off `ingest` management command stays.
- The `ingestor` service keeps working with the same entrypoint command; the scheduler's `django_apscheduler` app is available to any distribution that selects a plugin contributing jobs.
- A plugin may still expose its own management command and be run as a separate deployment; the shared scheduler is the default, not a requirement.
- Core's schema stops depending on ingestion so a distribution without it can migrate and run: the entity claim moves from `CatalogEntity.ingested_from` into an ingestion-owned `EntityClaim`, the composer no longer force-installs ingestion, and `atlas.database-schema` no longer requires the ingestion package. **BREAKING**: migrations of `catalog`, `ingestion`, `apis` and `database-schema` are regenerated from scratch (pre-release), so existing databases must be recreated.

Out of scope: any new job (search jobs come in a later change), a task queue, changing job intervals or settings names, and a UI for job management.

## Capabilities

### New Capabilities
- `core-scheduler`: the core-owned scheduler process, the plugin job-contribution hook, discovery across active plugins, and job pause/resume tied to plugin enablement.

### Modified Capabilities

## Impact

- `core/backend`: new `runapscheduler` management command and scheduler module; `django_apscheduler` becomes a core app; `CatalogEntity.ingested_from` and the matching `EntityService` parameter are removed; adopt writes the claim through ingestion; `catalog` migrations regenerated (plus a seed migration for the home settings).
- `plugin-api/python`: contract for the job-contribution hook next to `PluginDescriptor.job_ids`, an interval-job helper, and `ingested_from()`/`claim_relations()` reading the ingestion-owned claim.
- `plugins/ingestion`: scheduler module and command removed in favour of a `register_jobs` hook; behaviour of its jobs unchanged; new `EntityClaim` model and `claims` helpers; migrations regenerated.
- `plugins/apis`, `plugins/standard-catalog`: views load the claim through `claim_relations()`; `plugins/apis` and `plugins/database-schema` migrations regenerated; `database-schema` skips its facet-writer registration when ingestion is not installed.
- `composer`: no longer force-installs `atlas.ingestion` when a manifest omits it.
- `docs-site`: ingestion enablement wording, a pre-release changelog entry for the regenerated migrations, and the authentication migration runbook (no reverse migration for membership grants); the scheduler and plugin-jobs pages come with task 5.2.
- `docker-compose*.yml`, `render.yaml`, deployment docs: service keeps its command; naming and docs describe it as the platform scheduler rather than the ingestion scheduler.
- Existing tests for ingestion scheduling and plugin runtime job syncing move or adapt.
