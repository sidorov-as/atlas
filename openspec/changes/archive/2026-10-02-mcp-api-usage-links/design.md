## Context

The `atlas.apis` plugin owns two explicit join tables: `ServiceEndpointUsage` (service, endpoint) and `ServiceOperationUsage` (service, operation, role). They are written only by REST controllers in `atlas_plugin_apis/api/views.py` (`EndpointServicesController.post`, `OperationServicesController.post`, and the two `delete` controllers), which use session authentication. The create path for an endpoint link also calls `add_consumed_api` from the standard-catalog plugin so the Service's `consumesAPI` includes the API.

`atlas.mcp` already reads these links through `atlas_plugin_apis.extension_points` (`get_endpoint_consumers`, `get_operation_consumers`), which is the one sanctioned way for the MCP plugin to touch apis data: it never imports the apis models or controllers. MCP writes elsewhere use PAT scopes (`require_scope`), a `dryRun` flag built on `atlas_plugin_api.dry_run()` (a rolled-back transaction that also blocks outside side effects), and a published service rather than the ORM.

Scopes (`catalog:read`, `catalog:write`, `flows:read`, `flows:write`) are declared in core on `PersonalAccessToken`; the `scopes` column is a plain `JSONField`, so `SCOPE_CHOICES` feeds the admin form and `issue_pat` and is not part of a migration. Nothing outside the apis plugin writes the usage tables today, and the manifest format has no field that describes them.

Stakeholders: users who bulk-load a graph derived from a code analysis; the `atlas-curator` and `atlas-scout` skills; operators who issue PATs.

## Goals / Non-Goals

**Goals:**
- Create and remove Service-Endpoint and Service-Operation links from MCP, in batches large enough to load a whole graph, safely re-runnable.
- One implementation of the link rules shared by REST and MCP.
- Let a caller name a target either by id or by the key it has in hand (API, method, path / channel, direction).
- Record where a link came from (`origin`, `source`) and leave room for a manifest-declared origin.
- Teach the curator and scout skills to use the tools.

**Non-Goals:**
- Declaring these links in `catalog-info.yaml`; only the `yaml` origin value is reserved.
- Showing `origin` or `source` in the web UI or in existing REST responses.
- Storing evidence (file and line) or a client label with a link.
- A `apis:read` scope; read tools stay scope-free.
- Changing what `consumesAPI` does on unlink (it stays).

## Decisions

### 1. Link logic moves into extension points shared by REST and MCP

The create and delete logic (permission check on the Service, removed-endpoint check, duplicate check, document-owner check, `consumesAPI` side effect) moves out of the REST views into functions in the apis plugin's `extension_points.py`, each taking an `actor` and a `source`. The REST controllers become thin callers; the MCP controllers call the same functions.

Alternatives considered:
- *MCP calls the REST controllers or re-implements the rules.* Duplicates the rules and drifts, and the REST controllers are session-authenticated and shaped for HTTP.
- *MCP uses the models directly.* Breaks the rule that `atlas.mcp` never imports apis models, and makes `atlas.mcp` fail to import without `atlas.apis`.
- *Extension points (chosen).* Matches how reads already work and keeps one copy of the rules.

### 2. Four batch tools, one Service per call

Tools: `link_endpoint_consumers`, `unlink_endpoint_consumers`, `link_operation_participants`, `unlink_operation_participants`. Each takes one Service ref and a list of items. A single link is a batch of one, so there are no separate single-link tools.

Alternatives considered:
- *Single-link tools only.* A graph of thousands of links is thousands of tool calls, too slow and too costly in agent context.
- *A flat list of `(service, target)` pairs.* More general, but permission, error and `consumesAPI` reporting then mix Services in one response, and an agent working on a repository naturally has one Service at a time.
- *One tool each for link and unlink covering both endpoints and operations.* Fewer tools, but a polymorphic item shape and a role that only applies to one half make schemas and errors harder to read.
- *One Service per call, four tools (chosen).* Item shapes stay simple and permission is checked once per call. A caller with many Services sends one call per Service.

### 3. Addressing: exactly one of id or natural key per item

An item is either `{endpoint_id}` / `{operation_id}` or `{api, method, path}` / `{api, channel_address, direction}`. `api` is an API ref. An endpoint's key `(api, method, path)` is unique across all rows, removed ones included, so it identifies at most one Endpoint; linking to a removed one is a `conflict` and unlinking from it is allowed so stale links can be cleaned up. An operation's key `(api, channel, direction)` is not unique (the unique key is `(api, operation_key)`), so it resolves against active Operations only and ambiguity (more than one match) is reported, never resolved by picking one.

Alternatives considered:
- *Ids only.* The caller must search first, one call per target or a paged search; code analysis produces method and path, not ids.
- *Natural key only.* Drops the cheap path for an agent that has just searched and holds ids.
- *Both, exactly one per item (chosen).* The agent picks per context.

`ambiguous` can occur for operations only, since several operations of one API can share a channel and direction. The result lists candidate ids so the caller can retry with an id.

### 4. Partial success with per-item statuses; dry-run through the shared mechanism

Each item runs in its own savepoint. A failure in one item rolls back only that item. The response is a list of per-item results in request order plus counts per status. Request-level failures (missing scope, unknown Service, batch too large) reject the whole call. `dryRun` wraps the whole call in `atlas_plugin_api.dry_run()`, so statuses and counts come from the real code and nothing persists.

Alternatives considered:
- *All or nothing.* One stale endpoint in a 500-item import fails everything; the caller must find and remove it and resend.
- *Stop at the first error.* Order-dependent and still forces a rerun.
- *Partial success (chosen).* Idempotent reruns: items already done come back `unchanged`.

### 5. `origin` and `source` are columns on both models, set by the server

Both models get `origin` (`manual` | `yaml`, default `manual`) and `source` (`ui` | `mcp`). The extension-point functions take `source` as a parameter; the REST controllers pass `ui` and the MCP controllers pass `mcp`, so neither value comes from a request body. Removing a `yaml` link is rejected by the shared delete function, so REST and MCP behave the same. Django admin shows both fields. Existing rows are backfilled with `manual` and `ui`.

Alternatives considered:
- *No origin until ingestion exists.* Cheap now, but later means a migration of rows whose origin must be guessed. A default column now costs one migration.
- *One combined field.* `origin` (who owns the row's lifecycle) and `source` (how it was made) answer different questions; a `manual` link made over MCP and one made in the UI are both editable by hand, a `yaml` link is not.
- *Free-text provenance with evidence and client label.* Rejected for now; `ui` and `mcp` are enough.
- *Two columns (chosen).*

The `yaml` origin is read-only by rule only; nothing creates such a row yet, so that rule is covered by a test that inserts a row directly.

### 6. A new `apis:write` scope, declared in core

`PersonalAccessToken` gains `SCOPE_APIS_WRITE = "apis:write"` and a `SCOPE_CHOICES` entry, like `flows:write`. The MCP controllers call `require_scope(self, "apis:write")` before anything else. Core declares it even though the plugin is optional, as it does for flows; a token carrying a scope for an absent plugin is harmless.

Alternatives considered:
- *Reuse `catalog:write`.* Simpler, but then a token issued to edit entities can also rewrite the API dependency graph, and a crawler token cannot be limited to the graph.
- *Let the plugin register scopes.* Would need a new plugin extension mechanism for one scope; flows set the precedent for declaring it in core.
- *`apis:write` in core (chosen).*

Because `scopes` is a `JSONField` without `choices`, adding an entry to `SCOPE_CHOICES` needs no migration. The implementation confirms this with `makemigrations --check`.

### 7. Batch limit of 200 items

A call with more than 200 items is rejected whole, with the limit in the message. The value is a constant in the MCP plugin. Each item costs a handful of queries and the response carries a result per item; 200 keeps a call well inside a request timeout and the response readable for an agent. A caller with more sends several calls, which are safe to repeat.

Alternatives: no limit (unbounded request time and response size), 50 (too many calls for large graphs), and 1000 (a single call may run long). Revisit if real graphs show a different need.

### 8. `consumesAPI` reporting

The endpoint link result reports `api_relation_created` per item, as the REST response already does. The operation link has no such effect and its result has no such field. The side effect goes through `add_consumed_api` inside the same savepoint as the link, so a dry-run rolls it back with everything else.

### 9. Skills

`atlas-curator` gets a reference `usage-links.md` (addressing, batching per Service, reading statuses, dedupe via `get_*_consumers`, unlink confirmation) and a mention in its dependency order and its tool and scope tables. `atlas-scout` gets a plan row type for links, which it fills from `search_api_endpoints` and `search_api_operations`. The code location of a call site is shown to the reviewer in the plan only. Skills tell the user the `apis:write` scope is needed.

## Risks / Trade-offs

- **Natural key ambiguity or drift when a spec is re-imported** → Items come back `not_found` or `ambiguous` with the key and candidates, and the skills report them rather than guess.
- **A bulk caller can create many wrong links quickly** → `dryRun`, per-call limit of 200, `source` marking MCP-created links in admin so they can be found and cleaned, and a separate scope.
- **`consumesAPI` is added as a side effect and not removed on unlink** → Reported per item; documented in the tool description and skill reference. Existing behavior, not new.
- **`yaml` origin has no producer yet** → The read-only rule is tested with a directly inserted row; if the declaration never arrives, the column is dead weight but costs nothing.
- **Dry-run fidelity for the `consumesAPI` write** → It runs in the same rolled-back transaction as the link. Any side effect of `add_consumed_api` outside the database must honor `is_dry_run()`; the implementation checks that it has none and adds a dry-run warning if it does.
- **Refactor of the REST views could change their behavior** → Existing REST tests for both controllers stay unchanged and must pass.
- **Core declares a scope for an optional plugin** → Same as `flows:write`; accepted.

## Migration Plan

1. Add `origin` and `source` to both models in an apis plugin migration with defaults `manual` and `ui`, so existing rows are backfilled by the column default. The columns are added with defaults and are nullable-free, so the migration is a single expand step compatible with the repository's expand/contract rules.
2. Ship the extension-point refactor, the REST controllers on top of it, and the MCP tools together; REST responses do not change.
3. Add `apis:write` to core. No database migration is expected for it.
4. Roll back by reverting the code; the extra columns are unused by older code and can stay.

## Open Questions

- Whether the batch limit of 200 is right for the first real graph; to be tuned after the first import.
- None blocking. `direction` takes the values `send` and `receive` that the operation read tools already expose, and the key's `channel_address` is the same field those tools return.
