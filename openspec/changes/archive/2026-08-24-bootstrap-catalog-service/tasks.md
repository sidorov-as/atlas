## 1. Project scaffolding

- [x] 1.1 Django + django-modern-rest backend project scaffold
  - Use https://github.com/wemake-services/wemake-django-template 
- [x] 1.2 React + Vite frontend project scaffold with Gravity UI
- [x] 1.3 Docker Compose stack: `postgres`, `backend`, `frontend`, `ingestor`
- [x] 1.4 Wire Postgres connection and initial `manage.py migrate` in the backend service

## 2. Entity data model

- [x] 2.1 Abstract envelope base model (`name`, `title`, `description`, `labels`, `tags`, `links[]`) shared by all six kinds
- [x] 2.2 System, Component, Resource, API models with their kind-specific `spec` fields, using real FK/M2M for reference fields (`owner`, `system`, `dependsOn`, `providesApis`, `consumesApis`)
- [x] 2.3 Group and User models with their `spec` fields; `members`/`memberOf` as a single `ManyToManyField` serialized from both ends, not two independently-editable fields
- [x] 2.4 `ingested_from` nullable FK to `RegisteredRepository` on System/Component/Resource/API
- [x] 2.5 Shared ref resolver: `kind:name` string ↔ entity row, used by both serializers and ingestion
- [x] 2.6 Initial migration

## 3. Entity CRUD API

- [x] 3.1 Serializers and viewsets for System, Component, Resource, API (list/create/retrieve/update/delete)
- [x] 3.2 Read-only serializers/viewsets for Group and User (list/retrieve only)
- [x] 3.3 Validation: reference fields must point at existing entities
- [x] 3.4 `?owner=`, `?lifecycle=`, `?type=`, `?q=` filtering on list endpoints
- [x] 3.5 Ownership permission class: safe methods (list/retrieve) require only a session, with no ownership restriction; writes require `ingested_from is None` and owner-Group membership (or superuser)
- [x] 3.6 Apply the permission class to System/Component/Resource/API viewsets

## 4. Relations

- [x] 4.1 `Relation(subject_kind, subject_id, predicate, object_kind, object_id)` model
- [x] 4.2 Derivation logic: compute an entity's outgoing relations from its `spec` reference fields — all six pairs: `dependsOn`/`dependencyOf`, `providesApis`/`apiProvidedBy`, `consumesApis`/`apiConsumedBy`, `system`/`partOf`+`hasPart`, `owner`/`ownedBy`+`ownerOf`, `memberOf`/`hasMember`
- [x] 4.3 Recompute-on-write: delete and reinsert only the written entity's outgoing `Relation` rows, on both manual edit and ingestion upsert
- [x] 4.4 `GET /api/{kind}/{id}/relations/` returning both directions with correct forward/reverse predicates

## 5. Ingestion

- [x] 5.1 `RegisteredRepository` model and Django admin registration
- [x] 5.2 Connector interface: `list_manifest_paths`, `fetch_file`, `get_head_sha`
- [x] 5.3 `GitHubConnector` implementation against the GitHub REST API
- [x] 5.4 Manifest discovery: find `**/catalog-info.yaml` in each registered repo's default branch
- [x] 5.5 Multi-document (`---`-separated) manifest parsing
- [x] 5.6 Per-manifest schema validation; skip and log an invalid document without affecting the rest of the run
- [x] 5.7 Upsert: create or update by `(kind, name)`, set `ingested_from`, run each document in its own transaction
- [x] 5.8 Ingestor poll loop management command, wired into the `ingestor` Compose service

## 6. Diagrams

- [x] 6.1 `GET /api/diagrams/{kind}/{id}/?view=` — validate `(kind, id)` against real entities, validate `view` against the three allowed values
- [x] 6.2 Return a constant placeholder SVG for any valid target; 404 for unknown entity, 400 for invalid `view`

## 7. Auth

- [x] 7.1 Install and configure django-allauth in headless mode, local-account provider only
- [x] 7.2 Session + CSRF wiring for the SPA
- [x] 7.3 Login page and session-aware routing on the frontend

## 8. Web UI

- [x] 8.1 Systems list page: filterable/searchable table, "Add System"
- [x] 8.2 Components list page: filterable/searchable table, "Add Component", independent of any System's tabs
- [x] 8.3 Resources list page: filterable/searchable table, "Add Resource", independent of any System's tabs
- [x] 8.4 APIs list page: filterable/searchable table, "Add API", independent of any System's tabs
- [x] 8.5 System detail page: Overview, Components, Resources, APIs, Docs, Relations, C4 Diagram tabs
- [x] 8.6 Component detail page: Overview, Relations, C4 Diagram (component view) tabs — no Components/Resources/APIs/Docs tabs; Resource/API detail pages: Overview + Relations only, no C4 Diagram tab
- [x] 8.7 Teams (Groups) list & detail pages: members, owned entities
- [x] 8.8 Add/Edit forms for manual entities; read-only banner ("managed by `catalog-info.yaml` in `org/repo`") for YAML-managed entities
- [x] 8.9 Login page

## 9. Seed data

- [x] 9.1 Django admin access for creating initial Groups/Users (since Group/User creation has no API)
- [x] 9.2 Management command or fixture for seeding a first Group + superuser, so the stack is usable after first boot

## 10. Tests

- [x] 10.1 Entity CRUD: creation, ownership permission (member/non-member/superuser), YAML-managed read-only enforcement, non-owner read access is unrestricted, Group/User creation via API rejected
- [x] 10.2 Relations: derivation from spec fields for all six pairs (`dependsOn`, `providesApis`, `consumesApis`, `system`/`partOf`, `owner`, `memberOf`), including the case of one API both provided and consumed by different Components, both-direction listing, targeted recompute on write
- [x] 10.3 Ingestion: first ingest, re-ingest updates in place, invalid manifest skipped without affecting other documents in the run, multi-document file
- [x] 10.4 Diagram stub: valid target returns SVG, invalid id/view returns 404/400
- [x] 10.5 Auth: login establishes a session, unauthenticated request to a protected endpoint is rejected
