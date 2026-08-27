# Capability-to-documentation matrix

Baseline captured on 2026-09-12. This inventory guides the documentation
expansion. It does not promise that planned capabilities are available. A
capability is documented only when the cited manifest, specification,
configuration, command, or UI source is checked in.

Planned paths are relative to `docs-site/docs/` and may not exist until
their implementation task is done.

## Default-distribution feature coverage

The source of truth is `../../distributions/default/manifest.yaml`. The
manifest selects exactly the six plugin ids below. Each id must occur exactly
once in the machine-readable `plugin-id` front matter of a navigated feature
guide.

| Plugin id | Supported product surface | Current coverage | Required canonical guide |
| --- | --- | --- | --- |
| `atlas.standard-catalog` | Systems, Components, Resources, Teams/Actors, entity shell, ownership, relations, lifecycle | `plugin-development/built-in/standard-catalog.md`; concepts | `features/standard-catalog.md` |
| `atlas.apis` | API entities, spec sources, OpenAPI Endpoints, AsyncAPI Operations, dependency links and graphs | `plugin-development/built-in/apis.md` | `features/apis.md` |
| `atlas.c4` | Landscape, System Context, System Architecture, Component diagrams, viewer preferences and downloads | `plugin-development/built-in/c4.md` | `features/c4.md` |
| `atlas.database-schema` | Resource schema facet, SQL parsing, schema editor, ER diagram | `plugin-development/built-in/database-schema.md` | `features/database-schema.md` |
| `atlas.ingestion` | GitHub repositories, YAML discovery, parsing, claims, reconciliation, jobs and retries | `plugin-development/built-in/ingestion.md` | `features/ingestion.md` plus `features/integrations/github.md` |
| `atlas.flows` | Flow list/detail/editor, entity/Query/Event steps, transitions and layout | Missing | `features/flows.md` |

The current manifest contains no `plugins[].config` blocks. Configuration
guidance must distinguish the implemented typed configuration contract from
the configuration selected by this distribution.

## Documentation coverage ownership

Every product area is assigned below. Feature guides explain installed
behavior; task guides explain how to achieve an outcome; concept pages retain
the reusable model; reference pages hold exact contracts and identifiers.

| Documentation area | Primary documentation obligation |
| --- | --- |
| First launch and supported topology | `getting-started/` for the fresh-checkout journey; `operating-atlas/topologies.md` for runtime shape and constraints. |
| Authentication and authorization | Local and OIDC operator guides; identity and permissions concepts; permission registry reference. |
| Catalog domain and shared UI | Browsing, detail, manual editing, relationships, documentation, and tags in `using-atlas/`; reusable semantics in `concepts/`. |
| Entity lifecycle and provenance | Lifecycle task guides for YAML/manual ownership, conflicts, adoption, Remove, Revive, Purge, and Unavailable states; canonical lifecycle concept. |
| Standard Catalog feature | One complete `atlas.standard-catalog` feature guide, linked to catalog tasks and shared concepts. |
| APIs feature | `features/apis.md`, API user tasks, failure guidance for imports and refresh, and generated HTTP API links. |
| C4 feature | `features/c4.md` plus task links for landscape/entity diagrams, controls, rendering, and downloads. |
| Database Schema feature | `features/database-schema.md` covering edit, parse state, ER rendering, API, permissions, and failures. |
| Ingestion feature | Repository registration and troubleshooting tasks, `features/ingestion.md`, and GitHub integration guidance. |
| Flows feature | `features/flows.md` covering authoring, layout, references, permissions, API behavior, and limitations. |
| Distribution and plugin operations | Distribution, migrations, upgrade, plugin lifecycle, health, and symptom-oriented operator guides; exact manifest/lock and command references. |
| Plugin author contracts | Extension decision guide, first-plugin tutorial, backend/frontend contracts, configuration/secrets, testing, debugging, and Plugin API reference. |

## Runtime configuration coverage

The exact field reference will record the owner, type, default or required
state, secret handling, topology, and related guide. This table keeps fields
absent from `.env.example` in the documentation.

| Owner / source | Current keys or shape | Documentation destination and checks |
| --- | --- | --- |
| Settings selection (`core/backend/server/settings/__init__.py`) | `DJANGO_ENV` | Getting Started setup and configuration reference; accepted environment names must match checked-in settings modules. |
| Django/core (`core/backend/server/settings/components/common.py`) | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_STATIC_ROOT`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_CORS_ALLOWED_ORIGINS`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DJANGO_DATABASE_HOST`, `DJANGO_DATABASE_PORT`, `CONN_MAX_AGE`, `CATALOG_TITLE`, `CATALOG_DESCRIPTION` | Operator preflight and field reference. Mark signing key and database password secret; note that `DJANGO_STATIC_ROOT` and `CONN_MAX_AGE` are implemented even though the example env file omits them. |
| Production settings (`core/backend/server/settings/environments/production.py`) | required `DJANGO_ALLOWED_HOSTS`; `DJANGO_SECURE_SSL_REDIRECT` default `true`; secure cookies, proxy SSL header and HSTS | Production-like topology, host/origin checklist, and auth troubleshooting. |
| OIDC (`plugins/auth-oidc/backend`, common settings compatibility projection) | `discoveryUrl`, `expectedIssuer`, `clientId`, secret `clientSecret`, scopes/algorithms and `groupsClaim`; deprecated `OIDC_ISSUER` maps only to discovery | OIDC task guide and configuration reference. Require explicit issuer validation and selected-plugin runtime registration. |
| Ingestion (`core/backend/server/settings/components/common.py`) | `INGESTOR_POLL_INTERVAL` default `60` | Ingestion feature operations and configuration reference. |
| Compose (`docker-compose.yml`, `docker-compose.dev.yml`) | `ATLAS_PORT` default `8080`, `POSTGRES_HOST_PORT` default `5432`; service-specific database host overrides | Topology-specific startup and configuration reference. |
| Plugin configuration contract (`core/backend/server/apps/plugins/config.py`, `plugin-api/python/atlas_plugin_api/config.py`) | namespaced `plugins[].config`, typed schema, `{fromEnv: NAME}` secret references, explicit `PUBLIC_FIELDS` projection | Distribution guide, plugin-author configuration guide, and manifest reference. State that resolved secrets stay server-side and out of lock/generated/frontend artifacts. |
| Distribution (`distributions/default/manifest.yaml`, `distributions/default/lock.yaml`) | distribution/core versions; plugin id/version; backend/frontend package and source; disabled state, compatibility, config and integrity as supported by composer schemas | Distribution workflow and exact manifest/lock reference; validate examples with the composer. |

`core/backend/.env.example` remains the executable local template. Reconcile
the configuration reference with that file and the settings sources above;
neither source is complete on its own.

## Permission coverage

Explicit permission ids come from plugin `register_runtime()` hooks. Core
entity checks use the same evaluator with kind-derived ids even where those ids
are not separately registered.

| Surface | Permission contract | Who currently passes | Documentation destinations |
| --- | --- | --- | --- |
| Entity read | Authenticated session; evaluator convention `<kind>.read` where a resource check is made | Any authenticated principal | Catalog task guides and permissions concept. |
| Manual entity create/update/remove/revive/adopt | Ownership membership; writes use `<kind>.edit`; YAML-managed entities remain provenance-blocked | Superuser or Actor in the owner Group, subject to entity origin | Manual editing and lifecycle tasks; permissions concept. |
| Entity purge | `<kind>.purge` evaluated against the entity's owner | Purge Grant holder for the owner Group or superuser override | Purge task with irreversible-effect warning and grant prerequisites. |
| Tag colors | Superuser-only `TagWritePermission` | Superuser | Standard Catalog guide and permission registry reference. |
| C4 diagrams | `atlas.c4.diagram.read` | Any authenticated principal under the built-in evaluator | C4 feature guide. |
| API child reads | `atlas.apis.endpoint.read`, `atlas.apis.operation.read` | Any authenticated principal under the built-in evaluator | APIs feature guide and permission registry reference. |
| API child purge | `atlas.apis.endpoint.purge`, `atlas.apis.operation.purge`, scoped through the parent API owner | Parent API owner-Group Purge Grant holder or superuser override | APIs feature operations and lifecycle guidance. |
| Endpoint dependency links | `atlas.apis.endpointDependency.read`, `.create`, `.delete` | Any authenticated principal under the current evaluator; UI actions still reflect the evaluated result | APIs feature workflows and permission registry. |
| Operation dependency links | `atlas.apis.operationDependency.read`, `.create`, `.delete` | Any authenticated principal under the current evaluator; UI actions still reflect the evaluated result | APIs feature workflows and permission registry. |
| Flows | `atlas.flows.flow.read`, `atlas.flows.flow.edit`; edit is evaluated against the home System | Read: authenticated. Create/update/delete: home System owner-Group member or superuser | Flows feature guide and authoring tasks. |
| Database Schema facet | Reuses the owning Resource's edit check; no plugin-specific id | Resource owner-Group member or superuser | Database Schema feature guide. |
| Ingestion administration | No ingestion-specific permission id is registered; repository records are currently administered through backend/admin mechanisms | Administrative access as implemented | Ingestion and GitHub integration guides must not imply a catalog UI or finer-grained RBAC. |

Primary evidence: `core/backend/server/apps/catalog/api/permissions.py`,
`core/backend/server/apps/catalog/authorization.py`, and each default
plugin's `plugin.py`/`permissions.py`.

## Management-command coverage

Only project-owned commands are enumerated here. Framework commands such as
`migrate`, `collectstatic`, `check`, and `showmigrations` still appear in the
operator procedures that invoke them.

| Command | Behavior and risk | Required documentation |
| --- | --- | --- |
| `seed_admin` | Idempotently creates or updates the initial superuser, owner Group, and linked Actor using secret input from the environment, stdin, or an interactive prompt | Local-authentication bootstrap and management-command reference; never show a password argument. |
| `seed_booking_demo [--yes]` | Flushes the database, creates a disposable validated demo administrator, and creates the reproducible booking catalog | Getting Started demo step, screenshot data contract, command reference; mark destructive and explain interactive confirmation. |
| `seed_flow_layout_tests` | Recreates synthetic `test-*` Flows below its dedicated test System | Developer/debug reference only; do not present as general demo data. |
| `ingest` | Runs one ingestion pass and API spec refresh, then exits | Repository ingestion workflow, retries, and command reference. |
| `runapscheduler` | Starts blocking ingestion discovery/spec-refresh jobs and handles process shutdown | Ingestion operations and topology reference; it is a service entry point, not an ad-hoc retry command. |
| `check_migration_boundaries` | Fails when a plugin migration depends on another plugin instead of Core/itself | Plugin testing guide, migration operations, and command reference. |
| `purge_plugin <plugin_id> [--confirm]` | Dry-run table/row scope by default; `--confirm` deletes selected plugin-owned model rows transactionally | Plugin lifecycle operator guide and command reference with irreversible warning and selected-code prerequisite. |

Primary evidence: the project-owned `management/commands/*.py` files under
Core, Standard Catalog, and Ingestion, plus the Compose service commands.

## Supported UI workflow coverage

| UI surface | Checked-in behavior | Documentation destinations |
| --- | --- | --- |
| Session shell | Public `/login`; protected `/`; `/settings`; branded collapsible navigation | Getting Started login, local/OIDC auth, navigation tour. |
| Home | Catalog title/description plus the C4 System Landscape widget when C4 is selected | Overview, Getting Started visual tour, C4 feature guide. |
| Systems | List/search/filter/tags/status/pagination/preview; create/edit/remove; Overview, Components, Resources, APIs, Docs, Relations, History, Context and Architecture views | Catalog browsing/editing, lifecycle, relations, C4, and Standard Catalog feature guide. |
| Components | List/search/filter/tags/status/pagination/preview; create/edit/remove; Overview, Relations, History and Component diagram | Catalog browsing/editing, API dependencies, C4, Standard Catalog guide. |
| Resources | List/search/filter/tags/status/pagination/preview; create/edit/remove; Overview, Relations, History, Schema and ER Diagram tabs | Catalog browsing/editing and Database Schema guide. |
| Teams | List/search/pagination/preview and read-only detail with members and owned Systems/Components/Resources/APIs | Ownership guide, permission concept, Standard Catalog guide. |
| APIs | List/search/filter/tags/status/pagination/preview; create/edit/remove; Overview, Specification, Endpoints, Operations, Relations and History | Catalog tasks and APIs feature guide. |
| Endpoints and Operations | Dedicated detail pages; request/response or messages; removed/deprecated states; linked Services; search/filter/sort/pagination; link/unlink; consumer graphs | APIs feature guide and task-oriented dependency workflows. |
| C4 | `/architecture` landscape; System and Component diagram tabs; zoom/fit/settings/download preferences | C4 feature guide and visual catalog tour. |
| Database Schema | Resource Schema editor and ER Diagram tabs, including parse status/failure | Database Schema feature guide. |
| Flows | `/flows` list with system/team/search/pagination/preview and row actions; new/detail/edit pages; canvas authoring, manual/autolayout direction, Entity/Step/External/Query/Event nodes | Flows feature guide and task links from Systems/APIs. |
| Ingestion | No dedicated frontend contribution in the default distribution | Operator/admin repository workflow only; documentation must not invent a user-facing ingestion page. |

Primary evidence: composed routes, navigation items, detail-tab contributions,
and home widgets under `core/frontend/src/plugins/` and
`plugins/*/frontend/src/`, plus the corresponding frontend tests.

## Maintenance rule

When a capability, default plugin, configuration field, permission id,
management command, or composed UI contribution changes, the same change must
update this matrix or its eventual generated registries. Absence from the
default distribution must be stated as a limitation, not silently treated as
an unsupported or always-available feature.
