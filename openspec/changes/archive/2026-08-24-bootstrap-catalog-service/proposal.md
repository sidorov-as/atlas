## Why

Atlas has no implementation yet — `docs/design.md`, three ADRs, and `CONTEXT.md` fully describe the intended v1 slice, but there is no Django backend, no React frontend, no data model, and no Docker Compose stack. Nothing can be run, demoed, or built on top of until this exists — including the already-scoped `entity-claim-arbitration` change, whose tasks assume entity models, an ingestion upsert, and an owner-Group permission check that don't exist yet.

## What Changes

- Django + django-modern-rest backend project, React+Vite (Gravity UI) frontend project, Postgres, and a Docker Compose stack (`postgres`, `backend`, `frontend`, `ingestor`) — design.md §4.
- Entity envelope and basic CRUD for System, Component, Resource, API; read-only listing for Group and User (admin/ingestion-managed, not user-creatable) — design.md §3, §8.
- A minimal per-entity provenance marker distinguishing YAML-managed from manual entities, per the original (un-amended) ADR 0001: YAML-managed entities are read-only via the API and UI; manual entities are editable by members of their owner Group. Deliberately minimal — not the `source_kind`/repository-FK/arbitration model, which `entity-claim-arbitration` adds on top afterward.
- Derived relations materialized as a stored join table, both directions, recomputed per-entity on write — design.md §3.
- Ingestion pipeline: `RegisteredRepository` (Django-admin-managed), a connector interface with `GitHubConnector` as the only v1 implementation, discovery of `**/catalog-info.yaml`, a basic upsert (single-writer happy path — re-ingesting the same file updates the same entity; no first-claim arbitration), and failure handling that skips and logs one invalid manifest without rolling back the rest of the run — design.md §5.
- Diagram stub endpoint: `GET /api/diagrams/{kind}/{id}/?view={context|container|component}` returning a placeholder SVG for any valid target, 404/400 for an invalid one — design.md §6, ADR 0002.
- Auth: django-allauth headless, local-account only, session-based; ownership-based edit permission (member of the entity's owner Group, or superuser) — design.md §7, ADR 0003.
- Web UI: Systems/Components/Resources/APIs list pages (each independently browsable, not just reachable via a System's tabs), System/Component/Resource/API detail pages, Teams (Groups) list & detail, Add/Edit forms for manual entities with a read-only banner on YAML-managed ones, Login page — design.md §9.

No **BREAKING** changes — this is the first implementation; nothing exists to break.

## Capabilities

### New Capabilities
- `entity-catalog`: the entity envelope, `spec` fields per kind, and CRUD/listing endpoints for all six entity kinds.
- `entity-relations`: derivation and storage of typed relations from `spec` reference fields, both directions, and the `GET /api/{kind}/{id}/relations/` endpoint.
- `catalog-ingestion`: registered-repository config, the connector interface and `GitHubConnector`, manifest discovery, basic upsert, and per-manifest failure handling.
- `diagram-stub`: the placeholder C4 diagram endpoint and its validation of `(kind, id, view)`.
- `catalog-auth`: allauth-headless session login and the ownership-based edit permission rule.
- `catalog-web-ui`: the React pages listed above.

### Modified Capabilities
None — this change establishes the first specs in `openspec/specs/`.

## Impact

- **New services**: Django backend, React frontend, Postgres, ingestor poll loop, wired together via Docker Compose.
- **Data model**: entity tables for System/Component/Resource/API/Group/User, a relations join table, a `RegisteredRepository` table, and a minimal YAML-managed/manual provenance marker per ingestible entity.
- **REST API**: the full surface in design.md §8 except `POST /api/{kind}/{id}/adopt/` (added later by `entity-claim-arbitration`).
- **Sequencing**: `entity-claim-arbitration` depends on this change landing first — its tasks extend the provenance marker and entity base introduced here rather than creating them from scratch.
