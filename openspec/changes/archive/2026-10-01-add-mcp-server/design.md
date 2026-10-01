## Context

Atlas is a Django monolith composed from optional plugins via a manifest/composer system (`distributions/*/manifest.yaml`). Production runs under WSGI (`gunicorn server.wsgi:application`); an `asgi.py` entrypoint exists and shares the same plugin-composition bootstrap as `wsgi.py`/`manage.py`, but nothing in the deployment actually runs it today. `EntityService` (catalog) is already published as a `Protocol`-based singleton in `atlas_plugin_api`, obtained via `get_entity_service()`, whose methods take an `actor: Any` — it has no dependency on an HTTP request/session context. Flow has no equivalent: its CRUD lives directly in `plugins/flows/backend/atlas_plugin_flows/api/views.py`, calling permission helpers and the ORM inline. Atlas's `dmr` API framework already generates an OpenAPI document for the existing (SPA-facing) API. The composer's plugin schema (`PluginEntry`) only models installable `backend`/`frontend` Python/JS packages — it has no concept of "this plugin also runs its own standalone process," and its dependency mechanism (`requires_plugins`) is always mandatory (no optional-dependency variant); `atlas.c4`'s existing, deliberately code-level-only relationship to `atlas.apis` is the established pattern for an optional cross-plugin integration.

Comparable self-hosted platforms were reviewed for precedent: PostHog and Sentry both run their MCP server as a fully separate service (different language/repo even), calling their own public HTTP API rather than touching their Django/Python backend's internals. Flagsmith — the closest analog, a self-hosted Python/Django monolith — runs its MCP server as a separate FastMCP process that never imports Django; it calls Flagsmith's own REST API over `httpx`, and uses `FastMCP.from_openapi()` to generate tools from an OpenAPI document it already produces.

## Goals / Non-Goals

**Goals:**
- Expose a small, curated, LLM-tool-shaped surface for Atlas catalog entities and Flows, backed by the same authorize → validate → transaction → audit pipeline as the existing UI/REST paths.
- Keep the MCP wire-protocol transport fully decoupled from Atlas's Django process (deploy/scale/release independently; never run Django ORM under an async event loop).
- Make Flow tool availability track whether `atlas.flows` is actually installed in a given distribution, without making the whole MCP feature depend on it.
- Attribute every MCP-triggered write to the real human behind it, through Atlas's existing RBAC and audit trail.

**Non-Goals:**
- Publishing a versioned MCP transport image to a public registry, or any release CI pipeline for doing so — the transport's code and local `Dockerfile` are part of this change; publishing and operating a built image for a given deployment is left to whoever runs that Atlas instance.
- A full MCP OAuth 2.1 / OIDC resource-server flow (`Protected Resource Metadata`, discovery) — PAT Bearer auth is the v1 answer; OAuth is future work.
- Any change to the production WSGI entrypoint, `asgi.py`'s (currently unused) status, or the render single-container demo distribution.
- A general "plugin that also runs a process" concept in the composer/manifest schema.

## Decisions

### 1. MCP tools reach Atlas data over HTTP, not by importing Django in-process
Considered:
- **(a) In-process reuse, second process**: a dedicated process calls Django's bootstrap and invokes `EntityService`/`FlowService` as plain Python calls, no network hop. Cheapest at the data-access layer, but ties the MCP transport's language, release cadence, and process lifecycle to Django, and reopens the sync-ORM-under-async-transport question the moment the transport is an async framework.
- **(b) Top-level ASGI mount in the same process as the web app**: route `/mcp` to an MCP ASGI app and `/` to Django's own ASGI app in one process (Starlette-style). Rejected: Django's ORM is not genuinely async, so every tool call would need a thread-pool bridge anyway, for no benefit over (c); also changes the production entrypoint, which is explicitly out of scope.
- **(c) HTTP bridge** *(chosen)*: the MCP transport process holds no Django import at all and calls a new, curated Atlas HTTP API over `httpx`. Matches the reviewed precedent (all three), sidesteps the async-ORM question entirely (the transport process never touches the ORM), and keeps MCP's release cycle independent of Atlas core.

### 2. The curated API is new, not the existing SPA-facing API reused as-is
Considered:
- **(a) Point `from_openapi()` at Atlas's existing full OpenAPI document**: zero new backend code, but the existing document is UI-shaped (fine-grained CRUD, form-specific patch bodies) and would produce a chatty, badly-scoped tool list that silently changes whenever the SPA's needs change.
- **(b) Hand-write MCP tool functions calling `EntityService`/`FlowService` directly inside the transport process**: reads simplest, but requires Django in that process — excluded together with Decision 1(a).
- **(c) A new, small, purpose-built `dmr` controller module inside Atlas** *(chosen)*: exposes only `search_catalog`, `get_entity`, catalog writes, `list_flows`, `get_flow`, and Flow writes, publishing its own scoped OpenAPI document for `from_openapi()` to consume. Costs a dedicated module, but keeps the MCP tool surface intentional and independent of unrelated SPA changes.

### 3. `FlowService` extraction and the full Flow tool set ship in this same project
Considered:
- **(a) Catalog-only v1**: smallest slice; Flow tooling and `FlowService` extraction become an unrelated, indefinitely-deferred follow-up.
- **(b) Catalog + Flow read-only v1**: `list_flows`/`get_flow` reuse the existing ORM/permission helpers directly (no new service needed for reads); Flow writes wait for `FlowService` to exist as its own project.
- **(c) Catalog + full Flow read/write in one project** *(chosen, explicit stakeholder decision)*: accepts the larger initial scope — including extracting `FlowService` from the existing HTTP controllers — in exchange for shipping one coherent MCP surface instead of a visibly partial one.

### 4. Auth: per-user Atlas PAT, passed through verbatim
Considered:
- **(a) Single shared service-account PAT** for the whole MCP transport instance: simplest, and is in fact Flagsmith's own default. Rejected: collapses Atlas's per-user audit trail and RBAC scoping into one identity for every MCP-triggered action, regardless of which human actually triggered it.
- **(b) Full MCP OAuth 2.1 / OIDC resource-server flow**: the architecturally "correct" long-term answer per the MCP authorization spec, but a large scope (discovery, protected resource metadata, token exchange) disproportionate to a v1.
- **(c) Per-user Atlas PAT, forwarded by the transport as a Bearer header** *(chosen)*: the transport process stores no identity of its own; Atlas's new auth backend validates the token and resolves the real owning Django user as `actor`. (b) remains the explicit long-term direction.

### 5. Flow tools ↔ `atlas.flows` is an optional, code-level dependency
Considered:
- **(a) Hard `requires_plugins={"atlas.flows": ...}` manifest dependency** on the new plugin: rejected — composition treats every `requires_plugins` entry as mandatory (no optional variant exists in this codebase), which would make the *entire* plugin, including catalog tools that have nothing to do with Flow, uninstallable in any distribution lacking `atlas.flows`. Also contradicts the project's own documented rule to declare `requires_plugins` only when the contract cannot work at all without its owner.
- **(b) Publish Flow tools unconditionally, fail at call time** if `atlas.flows` isn't installed: rejected — surfaces an avoidable, late failure to whatever client invoked the tool, for a condition knowable at composition/tool-listing time.
- **(c) Optional, code-level dependency** *(chosen)*: mirrors `atlas.c4`'s existing relationship to `atlas.apis` — Flow tools (and their entries in the MCP OpenAPI document) are simply absent when `atlas.flows` isn't part of the distribution; no composition error, no runtime error.

### 6. New code location: a new, backend-only, distribution-selectable plugin
Considered:
- **(a) Inside an existing plugin** (`standard-catalog` or `flows`): rejected — mixes an orthogonal, cross-cutting concern into a plugin owned by unrelated functionality, and can't be independently excluded from a distribution.
- **(b) Atlas core, always present**: rejected — MCP is genuinely optional (e.g. not needed by the render demo), and Atlas's plugin system exists precisely to make features like this distribution-selectable.
- **(c) A new first-party plugin, backend-only** *(chosen)*: consistent with every other optional Atlas feature.

### 7. The MCP transport process itself lives outside composer entirely
Considered:
- **(a) Extend the composer/manifest schema** with a new "service" artifact kind so a distribution can declare "also run this process": rejected for v1 — premature generalization for a single consumer; no second case motivating it yet.
- **(b) Treat the transport process as a plugin backend artifact anyway** (install it as another Django app): not viable — by Decision 1 it is architecturally a separate process, not code joining the Django app registry.
- **(c) A separate, uncomposed directory in the repo** *(chosen)*: implemented in this same change as its own directory (outside composer/plugin-manifest awareness), with its own `Dockerfile` for a local build; whether/how a given deployment runs that container long-term (compose service, systemd unit, etc.) remains deployment-specific, but the code, build, and a documented stdio connection path ship with this change.

## Risks / Trade-offs

- **[Risk]** Bundling `FlowService` extraction into this change roughly doubles its size and touches a working, tested code path (Flow's existing HTTP controllers). → **Mitigation:** ship the extraction as its own reviewable milestone ahead of the MCP plugin work, with the existing Flow test suite re-run unmodified against the refactor — `flows-plugin`'s own spec already requires exactly this bar for any restructuring of Flow's implementation.
- **[Risk]** Per-user PAT pass-through means the transport process handles a live Atlas credential per configured end user; compromise of that process or its logs exposes those PATs. → **Mitigation:** PAT scopes narrow (never exceed) the holder's own RBAC; short default expiry; a dedicated security review is required before this ships in any production distribution.
- **[Risk]** A deactivated account's PAT must be rejected even though the token's own `revoked_at`/`expires_at` say nothing changed — easy to omit from the auth backend. → **Mitigation:** the PAT auth backend checks the owning account's active status on every request, not only the token's own fields; covered by a dedicated spec scenario and test.
- **[Risk]** The new curated MCP OpenAPI document and the existing SPA-facing one can drift apart in how each describes overlapping concepts (e.g. what a catalog entity looks like). → **Mitigation:** share the underlying schema/type definitions between both documents; let only the endpoint surface and grouping differ.
- **[Risk]** "Flow tools present only if `atlas.flows` is installed" is a new kind of runtime-conditional registration, unlike existing composition-time-only checks. → **Mitigation:** add a test mirroring `atlas.c4`/`atlas.apis`'s own optional-dependency test pattern, asserting the MCP OpenAPI document omits every Flow path when `atlas.flows` isn't selected.

## Migration Plan

1. Extract `FlowService` from `plugins/flows/backend/atlas_plugin_flows/api/views.py`; existing Flow REST controllers call it; existing Flow test suite passes unmodified.
2. Add the Atlas PAT model, an issuance path, and a PAT Bearer auth backend for `dmr`, independent of MCP.
3. Add the new plugin with read-only tools (`search_catalog`, `get_entity`, `list_flows`, `get_flow`), wired through the new curated API and PAT auth.
4. Add write tools (catalog create/update/delete via `EntityService`; `create_flow`/`update_flow`/`delete_flow` via `FlowService`), each running the same authorize/validate/transaction/audit pipeline as its HTTP-controller counterpart.
5. Security review of the full PAT + MCP-API surface before enabling it in any production distribution.
6. Implement the MCP transport process in its own repository directory (e.g. `mcp/`): a stdio-speaking bridge to the new curated API (Bearer PAT via env, e.g. `ATLAS_API_URL`/`ATLAS_PAT`), a `Dockerfile` for a local build, and documentation with an MCP-client config snippet (stdio `command`/`args`/`env`, matching the shape of e.g. `crystaldba/postgres-mcp`) plus an example prompt to verify the connection. Publishing a built image to a registry and any release pipeline for it stay out of scope — CI here only lints/builds/tests the directory like any other.

**Rollback:** the new plugin is an ordinary optional plugin — removing it from a distribution's manifest and recomposing removes the feature; the PAT table can remain unused with no data-migration concerns. Step 1 (`FlowService` extraction) is the only step touching existing behavior, and rolling it back means reverting that one refactor independent of every later step.

## Open Questions

- ~~Final PAT scope taxonomy...~~ **Resolved:** `catalog:read`, `catalog:write`, `flows:read`, `flows:write` (`PersonalAccessToken.SCOPE_CHOICES`). `catalog:read`/`flows:read` are accepted and stored but currently gate nothing — every read tool is open to any valid token — reserved for a future read gate rather than removed, so an operator can issue a read-scoped token today without it silently becoming a write-capable one later.
- ~~Whether the curated MCP OpenAPI document is a second document...~~ **Resolved:** its own `OpenAPIConfig` instance (`atlas_plugin_mcp.api.openapi.MCP_OPENAPI_CONFIG`, title "Atlas MCP API"), never merged with the SPA-facing one. It's also now HTTP-servable at a PAT-authenticated `GET /api/plugins/atlas.mcp/openapi.json` (`api/schema_views.py`, added alongside task 5.1's documentation) — needed because the transport process (Decision 1) holds no Django import and can't call `build_openapi_schema()` in-process.
- No target date is set for the full OAuth 2.1/OIDC resource-server flow (Decision 4, alternative b); it stays explicitly deferred.
