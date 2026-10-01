## Why

Atlas's MCP server is meant to let an AI client fill and edit the catalog through dialogue, but today its write surface cannot do that reliably. Verified against a running stack: `create_entity` with `spec.relationships` returns 201 yet persists no Architecture Relationship (only ingestion reconciles that field), and `update_entity` with a misspelled or unknown `spec` key returns 200 and changes nothing. A client therefore believes a write succeeded when it did not. There is also no way to author, inspect, or change Architecture Relationships over MCP, no way to learn a kind's `spec` fields and enums, and no way to preview a write before it is applied. Skills that drive the catalog through MCP need all of these before they can be trusted.

## What Changes

- Add a published `ArchitectureRelationshipService` so manual Architecture Relationship create, update, delete, and list logic lives in one place; the existing REST controllers and the new MCP tools both call it.
- Add MCP tools `list_relationships`, `create_relationship`, `update_relationship`, and `delete_relationship` for manual relationships. YAML-origin relationships stay read-only.
- **BREAKING**: `create_entity` and `update_entity` reject unknown `spec` keys with a 400 that names the offending key, instead of silently ignoring them. A `relationships` key in `spec` is rejected with a message pointing at the relationship tools. Callers that relied on silently ignored keys will now see errors.
- Add MCP tool `describe_kinds`, returning each MCP-writable kind's `spec` fields, enum values, limits, and required fields for create and for patch.
- Add a dry-run mode to `create_entity`, `update_entity`, `create_flow`, `update_flow`, `create_relationship`, `update_relationship`, and `delete_relationship` that runs all validation and authorization and returns what would change without persisting anything.
- Add MCP tool `validate_flow` that checks a flow body (entity refs, step ids, transition graph, mutual-exclusion rules, size limits) without saving.
- Update the MCP server's instruction text so clients know the new tools and the dry-run-then-write pattern.

Out of scope: manifest/ingestion authoring, new entity kinds, endpoint or operation write tools (those continue to come from spec parsing), Group or User writes, entity lifecycle tools (dependents report, restore, remove dry-run; a later change), and the skills that consume these tools (a separate change).

## Capabilities

### New Capabilities

- `mcp-relationship-tools`: MCP tools to list, create, update, and delete manual Architecture Relationships, with origin, source-kind, permission, and scope rules.
- `mcp-kind-introspection`: MCP tool that describes the writable kinds' `spec` shapes, enums, and limits so clients need not hard-code them.
- `mcp-write-preview`: dry-run mode for entity and flow writes and a `validate_flow` tool, so a client can show the user the effect of a write before applying it.

### Modified Capabilities

- `mcp-plugin`: the curated tool surface gains the new operations; entity writes enforce strict `spec` validation with explicit errors for unknown keys and for `relationships`; new operations also route through services only.
- `architecture-relationships`: manual relationship management is available through a published service contract shared by REST and MCP, with unchanged REST behavior.

## Impact

- `core/backend/server/apps/catalog`: extract relationship logic from the REST views into a service and publish its contract; REST controllers delegate to it.
- `plugins/mcp/backend/atlas_plugin_mcp`: new controllers and schemas, strict `spec` validation, dry-run support, curated OpenAPI updated.
- `plugins/standard-catalog` and `plugins/apis`: kind handlers expose field/enum metadata for `describe_kinds`; shared `*SpecIn` schemas keep working for ingestion.
- `plugins/flows`: `FlowService` gains a validate-only path used by dry-run and `validate_flow`.
- `plugin-api`: contract additions for the relationship service.
- `mcp/atlas_mcp/server.py` and `mcp/README.md`: instruction text and docs; no per-tool code, since tools are generated from the OpenAPI document.
- Existing MCP clients: tools are additive except the strict-validation change above.
