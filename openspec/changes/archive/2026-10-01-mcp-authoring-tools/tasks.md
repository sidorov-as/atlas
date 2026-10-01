## 1. Architecture Relationship service

- [x] 1.1 Define the `ArchitectureRelationshipService` Protocol and `get_architecture_relationship_service()` accessor in `plugin-api`, covering list-for-entity, create, update, delete
- [x] 1.2 Implement the service in core: manual-origin-only creation, YAML-origin mutation rejected, write permission checked on the source, source kind limited to System/Component/Resource/API, tags ensured
- [x] 1.3 Bind the implementation at startup the way `EntityService` is bound
- [x] 1.4 Switch the REST relationship controllers to call the service; keep their request and response shapes
- [x] 1.5 Add service-level tests for origin, permission, source-kind, and target-resolution rules; confirm existing relationship REST tests pass unchanged

## 2. Strict spec validation

- [x] 2.1 Add a key-check helper in `atlas_plugin_mcp` that compares `spec` and `metadata` keys with the target schema's field names and aliases and reports unknown keys with a closest-match hint
- [x] 2.2 Apply it in `create_entity` and `update_entity`, with the dedicated `relationships` message pointing at the relationship tools
- [x] 2.3 Ensure the create-side allowed set excludes `relationships` without changing the shared `*SpecIn` schemas used by ingestion
- [x] 2.4 Tests: misspelled key, unknown key on create and update, unknown `metadata` key, `relationships` rejected, nothing persisted on rejection
- [x] 2.5 Test that ingestion still reconciles `spec.relationships` as YAML-origin

## 3. Relationship MCP tools

- [x] 3.1 Add MCP-owned schemas for relationship input and output (including origin and id)
- [x] 3.2 Add controllers for `list_relationships`, `create_relationship`, `update_relationship`, `delete_relationship` with `catalog:read` / `catalog:write` scope checks
- [x] 3.3 Register the routes in `urls.py` and include the operations in the curated OpenAPI document
- [x] 3.4 Tests: create, partial update, delete, list with both directions and origin, YAML-origin rejection, non-writable source kind, unresolvable target, missing scope

## 4. Kind introspection

- [x] 4.1 Add `describe_kinds` that builds create and patch field schemas from the registered handlers' `spec_schema` and `patch_schema`, by alias, with enums, required fields, and limits
- [x] 4.2 Exclude `relationships` from create schemas; list only registered MCP-writable kinds; add the optional kind filter with a clear error for unknown or non-writable kinds
- [x] 4.3 Tests: Component and Resource enums, API fields when `atlas.apis` is installed, API absent when it is not, filter behavior, auth required

## 5. Dry-run

- [x] 5.1 Add a `dryRun` flag to the create/update operations for entities, flows, and relationships, and define the dry-run response envelope (`dryRun`, resulting state, field-level changes, warnings)
- [x] 5.2 Implement dry-run in the service layer as an operation inside a savepoint that is always rolled back, so validation, authorization, and reference resolution are the real ones
- [x] 5.3 Suppress the spec URL fetch in dry-run and return a warning instead
- [x] 5.4 Verify the generated MCP tool output schema handles the normal-or-dry-run response; fall back to a flat optional `dryRun` field if the union is not handled
- [x] 5.5 Tests: nothing persisted (rows and audit records) for every kind and for flows and relationships, same errors as a real write, write scope still required, no outbound request for `specSource` `url`, normal responses unchanged

## 6. Flow validation

- [x] 6.1 Expose a validate-only path on the flow service that collects all violations (refs, duplicate step ids, missing transition targets, cycles with step ids, step reference-field exclusion, size limits) without saving
- [x] 6.2 Add the `validate_flow` operation, present only when `atlas.flows` is installed, requiring `flows:read`
- [x] 6.3 Tests: valid flow, several violations reported together, cycle reported, absent without `atlas.flows`, scope enforced

## 7. Server instructions and docs

- [x] 7.1 Update the instruction text in `mcp/atlas_mcp/server.py` for the relationship tools, `describe_kinds`, and the dry-run-then-write pattern; keep the Flow-only text gated on the Flow tools
- [x] 7.2 Update `mcp/README.md` and the documentation site's MCP page with the new tools and the strict-validation behavior
- [x] 7.3 Add a release note describing the strict-validation breaking change

## 8. Verification

- [x] 8.1 Run the MCP plugin, core catalog, and flows test suites and `make ci`
- [x] 8.2 Re-run against a local dev stack: create an entity with `spec.relationships` is rejected, a relationship is created through the new tool and appears in the listing, a dry-run changes nothing, and `describe_kinds` matches the handlers
