## 1. Contract

- [x] 1.1 Document the `register_jobs(scheduler)` hook next to `PluginDescriptor.job_ids` in the plugin API package
- [x] 1.2 Add a small helper for registering an interval job with the standard connection handling, single-instance and replace-existing defaults

## 2. Core scheduler

- [x] 2.1 Add the scheduler builder over the shared persistent job store to core
- [x] 2.2 Add the core `runapscheduler` management command with clean SIGINT/SIGTERM shutdown
- [x] 2.3 Discover and call `register_jobs` on every active selected plugin, skipping plugins without the hook and disabled plugins
- [x] 2.4 Fail startup when a hook registers a job id missing from the plugin descriptor, naming the plugin and id
- [x] 2.5 Add `django_apscheduler` to the core installed apps and verify migrations apply on a distribution without ingestion
  - [x] 2.5a Move the entity claim into ingestion (`EntityClaim`, `claims` helpers), drop `CatalogEntity.ingested_from` and the `EntityService` parameter, and read it through `ingested_from()`/`claim_relations()` (design Decision 7)
  - [x] 2.5b Regenerate the `catalog`, `ingestion`, `apis` and `database-schema` migrations, add the home-settings seed migration, and drop tests of the removed backfill migrations
  - [x] 2.5c Stop the composer force-installing ingestion when a manifest omits it
  - [x] 2.5d Make `atlas.database-schema` skip its facet-writer registration when the ingestion package is not installed, with a test

## 3. Migrate ingestion

- [x] 3.1 Implement `register_jobs` in the ingestion plugin using the helper, keeping job ids, interval setting and single-instance behaviour
- [x] 3.2 Remove the ingestion scheduler module and old `runapscheduler` command, and drop `django_apscheduler` from the plugin's own apps
- [x] 3.3 Keep the one-off `ingest` command using the same job functions
- [x] 3.4 Confirm a distribution without ingestion starts `runapscheduler` without importing ingestion code (checked with the ingestion package blocked from import)

## 4. Tests

- [x] 4.1 Unit-test hook discovery: active plugin, plugin without hook, disabled plugin
- [x] 4.2 Unit-test undeclared job id failure
- [x] 4.3 Test pause on disable and resume on enable still hold with the core scheduler
- [x] 4.4 Test that a raising job does not stop others and overlapping runs are skipped
- [x] 4.5 Adapt existing ingestion scheduling tests to the new location (there were none; added tests for the ingestion `register_jobs` contribution)
- [x] 4.6 Add a regression test that a migrations run and app start succeed with ingestion deselected, and that ingestion-managed entities still reject manual writes

## 5. Deployment and docs

- [x] 5.1 Verify compose and Render configs run the unchanged command and rename wording from "ingestion scheduler" to "scheduler"
- [x] 5.1a Verify the public demo image still builds and runs without a scheduler, with the scheduler app's migrations applied at build time
- [x] 5.2a Update docs-site for the dependency change: ingestion enablement wording, the removed membership-grant reverse migration, and a pre-release changelog entry for the regenerated migrations
- [x] 5.2 Document in the docs site how a plugin contributes jobs and how to run a plugin's work as a separate deployment
- [x] 5.3 Run the full local CI target and fix regressions
- [x] 5.4 Review all documentation (docs-site, READMEs, `docs/`, examples, Compose and Render comments) for anything this change forgot to add or update, and fix or list what remains
