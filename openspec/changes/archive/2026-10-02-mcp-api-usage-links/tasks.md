## 1. Core: apis:write scope

- [x] 1.1 Add `SCOPE_APIS_WRITE = "apis:write"` and a `("apis:write", "APIs: write")` entry to `SCOPE_CHOICES` in `core/backend/server/apps/catalog/models/personal_access_token.py`
- [x] 1.2 Confirm `python manage.py makemigrations --check` needs no migration for the scope (the `scopes` field is a plain `JSONField`)
- [x] 1.3 Add tests: `issue_pat` accepts `apis:write`, still rejects an unknown scope; the admin form lists it

## 2. atlas.apis: origin and source

- [x] 2.1 Add `origin` (`manual` | `yaml`, default `manual`) and `source` (`ui` | `mcp`, default `ui`) to `ServiceEndpointUsage` and `ServiceOperationUsage`, with choices constants next to the models
- [x] 2.2 Add the apis plugin migration that adds both columns with those defaults, so existing rows become `manual` / `ui`; check it against the repository's expand/contract rules
- [x] 2.3 Show `origin` and `source` (read-only) in `ServiceEndpointUsageAdmin` and `ServiceOperationUsageAdmin`; keep them out of every REST schema and the web UI
- [x] 2.4 Add a migration test: rows that exist before the migration have `origin=manual`, `source=ui`

## 3. atlas.apis: shared link functions

- [x] 3.1 Add to `extension_points.py` link and unlink functions for endpoints and operations, each taking `actor`, the Service, a target, and `source` (and `role` for operations), carrying today's rules: dependency create/delete permission on the Service, removed-endpoint conflict, duplicate detection, document-owner conflict for operations, the `consumesAPI` side effect on endpoint link, and no `consumesAPI` change on unlink
- [x] 3.2 Make the link functions record `origin=manual` and the given `source`, and the unlink functions reject a `yaml`-origin link with a conflict that says it is managed by ingestion
- [x] 3.3 Add target resolution helpers: by id; by `(api ref, method, path)` for an endpoint (one row at most, status not filtered); by `(api ref, channel_address, direction)` for an operation (active only, may return several)
- [x] 3.4 Rewrite the four REST controllers (`EndpointServicesController.post`, `EndpointServiceController.delete`, `OperationServicesController.post`, `OperationServiceController.delete`) as thin callers passing `source="ui"`; their responses and status codes stay as they are
- [x] 3.5 Run the existing REST tests for these controllers unchanged and make them pass; add tests for the `yaml` rejection through REST, using a row inserted directly, and for a `yaml` publisher link surviving the unlink of the same Service's `subscriber` link

## 4. atlas.apis: batch operation

- [x] 4.1 Add a batch function per tool that takes the Service, the items, and a dry-run flag, runs each item in its own savepoint, and returns one result per item in request order with its status and the per-status counts
- [x] 4.2 Implement the statuses: link `created` / `unchanged` / `not_found` / `ambiguous` / `conflict` / `invalid`; unlink `removed` / `unchanged` / `not_found` / `ambiguous` / `conflict` / `invalid`; include candidate ids for `ambiguous` and, for endpoint links, `api_relation_created`
- [x] 4.3 Validate each item's shape (exactly one of id or complete natural key; operation items need `role`) and mark a bad item `invalid` without stopping the batch
- [x] 4.4 Reject the whole request for an unresolvable Service, a Service that is not a Component, a missing permission on the Service, and a batch over 200 items (constant, with the limit in the message)
- [x] 4.5 Make `dryRun` wrap the batch in `atlas_plugin_api.dry_run()`; check that `add_consumed_api` has no side effect outside the database, and call `add_dry_run_warning` if it does
- [x] 4.6 Add tests: partial success with one stale item; idempotent rerun gives `unchanged`; natural key and id forms; both forms or neither gives `invalid`; ambiguous operation key; removed endpoint by id and by key gives `conflict` on link and `removed` on unlink; document owner gives `conflict`; both roles on one operation; `consumesAPI` reported on the first link and not on the second; dry-run leaves no rows and no `consumesAPI`; oversized batch rejected

## 5. atlas.mcp: tools

- [x] 5.1 Add MCP-owned request and response schemas in `plugins/mcp/backend/atlas_plugin_mcp/api/schemas.py` for the four tools: Service ref, items (id or natural key), role, `dryRun`, per-item results, counts
- [x] 5.2 Add `plugins/mcp/backend/atlas_plugin_mcp/api/usage_views.py` with four controllers with explicit `operation_id`, `summary`, and `description` (`link_endpoint_consumers`, `unlink_endpoint_consumers`, `link_operation_participants`, `unlink_operation_participants`); each calls `require_scope(self, "apis:write")` first and then only `atlas_plugin_apis.extension_points` with `source="mcp"`, importing no apis model or REST controller
- [x] 5.3 Resolve the Service ref through the same ref machinery the relationship tools use, and reject non-Component kinds
- [x] 5.4 Wire the controllers into `_api_urls()` in `atlas_plugin_mcp/api/urls.py`, under the existing `atlas_plugin_apis` installed check
- [x] 5.5 Add tests: the MCP OpenAPI document has all four tools with the short `operationId`s when `atlas.apis` is installed and none when it is not; a PAT with `catalog:write` but not `apis:write` is rejected; a PAT with `apis:write` cannot exceed its owner's permissions; created links have `origin=manual`, `source=mcp`, and the PAT owner as creator; a link made over REST is `unchanged` when sent over MCP
- [x] 5.6 Add a test that the tool descriptions state the `apis:write` scope, the 200-item limit, and the `consumesAPI` side effect

## 6. MCP server transport and documentation

- [x] 6.1 Extend the conditional `instructions` text in `mcp/atlas_mcp/server.py` with a short paragraph present only when the fetched OpenAPI document lists the usage tools: when to use ids and when natural keys, to batch per Service, to read per-item statuses, and to use `dryRun` first for removals
- [x] 6.2 Add or update `mcp/tests/test_server.py` for that conditional text
- [x] 6.3 Verify against a real backend-generated OpenAPI document that `FastMCP.from_openapi()` yields clean names and non-empty descriptions for the four tools
- [x] 6.4 Update `docs-site/docs/features/mcp.md`: four rows in the tool table, `apis:write` in the scope table, a short section on addressing, per-item statuses, `dryRun`, and the `consumesAPI` side effect; note that `origin` and `source` appear in Django admin only

## 7. Skills

- [x] 7.1 Add `skills/atlas-curator/references/usage-links.md`: when to use each addressing form, batching per Service, dedupe with `get_endpoint_consumers` / `get_operation_consumers`, reading statuses, not guessing a replacement for `not_found` / `ambiguous`, the `consumesAPI` note, YAML-origin links, and confirmed unlinking with `dryRun`
- [x] 7.2 Update `skills/atlas-curator/SKILL.md` and `references/shared-rules.md`: the write order puts links last, after the API specification is attached and its endpoints or operations are confirmed; add the new tools and the `apis:write` scope to the tool and scope tables; replace the "never written directly" wording about endpoints and operations so it separates the endpoints themselves (still derived) from the links to them
- [x] 7.3 Update `skills/atlas-scout/references/plan-format.md` and `discovery.md`: a link row type `(service -> endpoint/operation, role)`, taken from `search_api_endpoints` / `search_api_operations`, with the code location as reviewer-only text, and call sites with no match listed as undetermined
- [x] 7.4 Update `skills/atlas-flow/references/tools-and-scopes.md` and `skills/README.md` with the new tools and scope; keep `skills/VERIFICATION.md` in step with the new behaviors
- [x] 7.5 Run the skills check workflow's validation locally (as `.github/workflows/skills-check.yml` does) and fix any failure

## 8. Final verification

- [x] 8.1 Run the apis plugin, mcp plugin, core, and `mcp/` test suites and the local CI run
- [x] 8.2 Against a local stack, load a small graph end to end: create an OpenAPI and an AsyncAPI API, confirm endpoints and operations were parsed, link a Service with `dryRun` and then for real by natural key, rerun to see `unchanged`, check the links in the web UI's Linked Services tabs and `source=mcp` in Django admin, then unlink with `dryRun` and for real
