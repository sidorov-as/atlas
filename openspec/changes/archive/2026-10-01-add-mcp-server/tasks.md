## 1. FlowService extraction (flows-plugin)

- [x] 1.1 Design `FlowService`'s interface (list/get/create/update/delete) mirroring `EntityService`'s shape (`actor` parameter, same exception conventions) and publish it via `atlas_plugin_flows`'s own `.contracts`/`.extension_points` submodule pattern
- [x] 1.2 Move Flow create/update/delete/list/get logic out of `plugins/flows/backend/atlas_plugin_flows/api/views.py` and into `FlowService`, preserving existing `can_edit_flow`/`check_flow_write_permission` checks exactly
- [x] 1.3 Refactor the existing Flow REST controllers (`views.py`) to call `FlowService` instead of the ORM/permission helpers directly
- [x] 1.4 Run the full existing Flow test suite unmodified against the refactor; fix only what the refactor itself broke
- [x] 1.5 Add a test asserting another plugin can call `FlowService` without importing `atlas_plugin_flows` internals

## 2. Atlas Personal Access Tokens

- [x] 2.1 Add the PAT model: hash + short lookup prefix (never plaintext at rest), scopes, `expires_at`, `revoked_at`, `last_used_at`, owning user FK
- [x] 2.2 Add token issuance (UI and/or management command) that displays the plaintext exactly once
- [x] 2.3 Add token validation: hash/prefix lookup, `expires_at`/`revoked_at` checks, and owning-account active-status check
- [x] 2.4 Update `last_used_at` on every successful authentication
- [x] 2.5 Add a `dmr` Bearer auth backend that resolves a valid PAT to its owning Django user
- [x] 2.6 Write tests for: successful issuance, expired token, revoked token, deactivated-owner token, scope narrowing against RBAC, `last_used_at` update

## 3. mcp-plugin: read-only tools

- [x] 3.1 Scaffold the new `atlas.mcp` plugin (backend-only `PluginEntry`, no `requires_plugins` on `atlas.flows`)
- [x] 3.2 Add a new, scoped `dmr` controller module exposing `search_catalog` and `get_entity`, backed by `EntityService`, with its own `OpenAPIConfig`/document distinct from the SPA-facing API
- [x] 3.3 Wire the PAT Bearer auth backend (from Task 2.5) into this controller module; reject requests with no/invalid/expired/revoked/inactive-owner tokens
- [x] 3.4 Add runtime detection of whether `atlas.flows` is installed (mirroring `atlas.c4`'s existing optional, code-level dependency on `atlas.apis`); conditionally register `list_flows`/`get_flow` only when present, backed by `FlowService`
- [x] 3.5 Add a test asserting the MCP OpenAPI document omits every Flow-related path when `atlas.flows` isn't selected, and includes them when it is
- [x] 3.6 Add the new plugin to every distribution manifest except the render single-container demo

## 4. mcp-plugin: write tools

- [x] 4.1 Add catalog create/update/delete operations to the MCP controller module, backed by `EntityService`, applying the same authorize/validate/transaction/audit pipeline as the existing REST write paths — shipped as `create_entity`/`update_entity`/`remove_entity`/`purge_entity` (no raw `delete_entity`): the REST API itself has no single-step delete, having retired `EntityService.delete()` in favor of Remove→Purge (D14), so MCP matches that same two-step path rather than exposing a weaker one of its own. Writes are restricted to the kinds REST itself lets anyone write (System/Component/Resource/API) — Group/Actor stay read-only through MCP too. `EntityKindHandler` gained a `patch_schema` field (alongside the existing `spec_schema`) so this stayed kind-agnostic instead of hardcoding per-plugin schema imports.
- [x] 4.2 Add `create_flow`/`update_flow`/`delete_flow` operations, backed by `FlowService`, conditionally registered per Task 3.4's mechanism
- [x] 4.3 Add PAT scope enforcement: deny a write operation whose token scope doesn't cover it, independent of the underlying user's own RBAC
- [x] 4.4 Add tests asserting MCP-triggered writes produce audit records indistinguishable (other than actor) from the same write via the existing REST API
- [x] 4.5 Add tests asserting RBAC-denied and scope-denied writes are both rejected

## 5. Documentation and review

- [x] 5.1 Document the curated MCP tool set, its OpenAPI document location, and PAT issuance/scopes in `docs-site`
- [x] 5.2 Document that the MCP transport process is not composer/manifest-aware (it isn't a plugin), pointing to `mcp/`'s own README (Task 6.4) for how to build, run, and connect it
- [x] 5.3 Run a dedicated security review of the PAT + MCP-API surface before enabling `atlas.mcp` in any production distribution

## 6. MCP transport process (`mcp/`)

- [x] 6.1 Scaffold the `mcp/` directory at the repo root, outside `plugins/`/`composer`/`distributions`
- [x] 6.2 Implement the MCP server: stdio transport to the client, `httpx`-based client to the new curated Atlas API, Bearer PAT read from env (e.g. `ATLAS_API_URL`, `ATLAS_PAT`)
- [x] 6.3 Add a `Dockerfile` for a local build (`docker build`); no registry publish step
- [x] 6.4 Write a README with an MCP-client config snippet (stdio `command`/`args`/`env`, matching the shape of `crystaldba/postgres-mcp`'s config) and an example prompt to verify the connection end-to-end
- [x] 6.5 Add this directory to the repository's existing CI (lint/build/tests), matching how other components are checked, with no image-publish step
