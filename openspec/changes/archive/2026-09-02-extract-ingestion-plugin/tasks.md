## 1. Scaffold and move as-is

- [x] 1.1 Create `plugins/ingestion/backend/` declaring a manifest dependency on `atlas.standard-catalog`.
- [x] 1.2 Move `RegisteredRepository`, conflict-record models, `GitHubConnector`, and the `catalog-info.yaml` parser into the plugin unchanged (no behavior change yet).
- [x] 1.2.1 Move the discovery-run scheduling loop onto `django-apscheduler`, registered under a plugin-owned job id.
- [x] 1.3 Verify `catalog-ingestion`/`entity-claim-arbitration` scenarios pass against the moved-but-unrewired code.

## 2. Extension points and EntityIntent

- [x] 2.1 Add `atlas.ingestion.connectors.v1` and `atlas.ingestion.parsers.v1` keyed extension points; register `GitHubConnector` and the YAML parser against them.
- [x] 2.2 Add the `EntityIntent` value type.
- [x] 2.3 Add a `source` parameter to `EntityService.create`/`.update` (`manual` vs `yaml`, carrying `ingested_from`).

## 3. Rewire the write path

- [x] 3.1 Rewire plain System upsert through `EntityIntent` → `EntityService`; verify `catalog-ingestion`/`entity-claim-arbitration` System scenarios.
- [x] 3.2 Repeat for Component, Resource, API, verifying each kind's scenarios.
- [x] 3.3 Rewire Architecture Relationship reconciliation to depend on the new entity-upsert path; verify `architecture-relationships` ingestion scenarios.

## 4. Cleanup

- [x] 4.1 Delete the old direct-write upsert code from `server.apps.ingestion`.
- [x] 4.2 Confirm the adoption endpoint (`POST /api/{kind}/{id}/adopt/`) and conflict-visibility banner behavior are unaffected.
- [x] 4.3 Compose a distribution without `atlas.ingestion`; verify manual/API entity management is unaffected.
