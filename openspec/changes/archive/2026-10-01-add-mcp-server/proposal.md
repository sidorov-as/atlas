## Why

Atlas has no way for MCP clients (Claude Desktop, other LLM tools) to read or act on catalog and Flow data. Doing this well means exposing a small, curated, LLM-shaped tool surface backed by Atlas's existing authorization/validation/audit pipeline — not a raw dump of every internal HTTP endpoint, and not a bespoke reimplementation of RBAC inside a separate protocol server. The MCP transport itself (protocol framing, session handling) should stay fully decoupled from Atlas's Django/WSGI process so the two can evolve, deploy, and scale independently, matching how comparable self-hosted platforms (e.g. Flagsmith) structure their own MCP integration.

## What Changes

- Add a new optional Atlas plugin (`atlas.mcp`, working name) that publishes a small, curated HTTP API purpose-built for MCP tool calling — `search_catalog`, `get_entity`, and catalog write operations backed by the existing `EntityService`; `list_flows`, `get_flow`, `create_flow`, `update_flow`, `delete_flow` backed by a new `FlowService`. This API has its own OpenAPI document, separate from the existing SPA-facing API, sized for tool-calling rather than UI CRUD.
- The plugin declares only an **optional, code-level** dependency on `atlas.flows` (matching the existing `atlas.c4` ↔ `atlas.apis` pattern) — not a manifest `requires_plugins` entry. Flow tools are simply absent from the tool list when `atlas.flows` isn't installed in the distribution; composition never fails and no tool call ever errors for this reason.
- Add Atlas Personal Access Tokens: a new token type a user can issue (plaintext shown once), stored as hash + short lookup prefix, carrying scopes that narrow (never replace) the holder's existing RBAC, with `expires_at`/`revoked_at`/`last_used_at`. Validation rejects a token whose owning account is no longer active, independent of the token's own `revoked_at`.
- Add a PAT-based Bearer auth backend for the new API, resolving a validated token to its owning Django user and passing that user as `actor` into `EntityService`/`FlowService`, so every MCP-triggered write flows through the same authorize → validate → transaction → audit pipeline as any other write.
- **Extract `FlowService`** from `plugins/flows/backend/atlas_plugin_flows/api/views.py`: today Flow create/update/delete/list/get logic lives directly in HTTP controllers with no service layer. `FlowService` becomes the one path both the existing Flow REST controllers and the new MCP plugin call, so the two never diverge in validation or permission checks.
- Add the MCP transport itself: a process (e.g. a FastMCP instance) that speaks the MCP wire protocol to external clients (Claude Desktop, Codex, Qwen, etc.) and calls the new curated HTTP API above. It lives in its own directory in this repository, outside `plugins/`/`composer`/`distributions` — this change does not add any manifest/composer concept for "a plugin that also runs its own process." It ships with a `Dockerfile` for a local build and documentation showing a stdio MCP-client config (command/args/env, matching the shape of e.g. `crystaldba/postgres-mcp`) plus an example prompt to verify the connection.
- **Out of scope:** publishing a versioned image to a public registry (e.g. `ghcr.io`) and any release pipeline for it. CI for this repository only needs to lint/build/test the new directory like any other; publishing and operating an image for a given deployment is left to whoever runs that Atlas instance.

## Capabilities

### New Capabilities
- `mcp-plugin`: the optional Atlas plugin exposing a curated, MCP-tool-shaped HTTP API (catalog search/read/write via `EntityService`, Flow read/write via `FlowService`) with its own OpenAPI document; Flow tools are present only when `atlas.flows` is also installed, via an optional code-level dependency, never a hard manifest dependency.
- `personal-access-tokens`: issuance, storage (hash + prefix, never plaintext at rest), scopes, expiry/revocation, last-used tracking, and validation that also treats a deactivated owning account as invalid.

### Modified Capabilities
- `flows-plugin`: adds the requirement that Flow create/update/delete/list/get is available through a published `FlowService` contract, not only through the existing HTTP controllers, so other code (specifically the new `mcp-plugin`) can perform the same operations without duplicating authorization, validation, or transaction handling.

## Impact

- New Django app/plugin under `plugins/mcp/backend/` (or similar), composer-selectable per distribution like any other first-party plugin; excluded from the render single-container demo distribution.
- New `FlowService` module extracted from `plugins/flows/backend/atlas_plugin_flows/api/views.py`; existing Flow REST controllers refactored to call it instead of the ORM/permission helpers directly, with no change to existing REST behavior, routes, or response shapes.
- New Atlas PAT model, issuance UI/management command, and Bearer auth backend for `dmr`, independent of the existing cookie/session auth used by the SPA.
- No changes to the production WSGI entrypoint (`gunicorn server.wsgi:application`); no change to `core/backend/server/asgi.py`'s (currently unused) status.
- A new, non-composer directory in this repository (e.g. `mcp/`) holding the MCP transport process (e.g. a FastMCP instance): its own `Dockerfile`, buildable locally, and documentation for connecting an MCP client via stdio. Publishing a built image to a registry, and any CI release pipeline for that, is left to whoever deploys a given Atlas instance.
