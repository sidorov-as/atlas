## Context

`atlas.mcp` exposes a curated HTTP API, and `mcp/atlas_mcp` turns its OpenAPI document into MCP tools with `FastMCP.from_openapi()`; no tool is hand-written. Catalog writes go through the published `EntityService`, flow writes through `FlowService`. Both are Protocols in a contract package with a `get_*_service()` accessor, implemented by core or by the flows plugin.

Verified against a running stack, three gaps block AI-driven catalog authoring:

1. `create_entity` accepts `spec.relationships` and returns 201, but persists nothing. The field exists on the shared `*SpecIn` schemas only because ingestion reads it and reconciles YAML-origin relationships. `update_entity` validates against `*SpecPatch` schemas, which use pydantic's default `extra="ignore"`, so any unknown or misspelled `spec` key returns 200 and changes nothing.
2. Manual Architecture Relationships have REST CRUD in core, but its logic sits inside the view classes (direct ORM, session auth) and is not reachable from MCP.
3. A client cannot discover a kind's `spec` fields or enums except by reading source, and cannot see the effect of a write before applying it.

Constraints: the `mcp-plugin` spec requires MCP operations to go through services and never direct ORM; plugins may import only contract packages, not core internals or each other's implementation; ingestion keeps using the shared `*SpecIn` schemas.

## Goals / Non-Goals

**Goals:**
- A client can create, read, update, and delete manual Architecture Relationships over MCP with the same authorization as the web UI.
- A client can never be told a write succeeded when part of it was ignored.
- A client can learn the writable kinds' shapes from the server instead of from hard-coded copies.
- A client can preview any authoring write and show the user what will change before applying it.

**Non-Goals:**
- Writing manifests or changing ingestion behavior.
- New entity kinds, or writes to Group/User.
- Writing API endpoints or operations (they stay derived from spec parsing).
- Entity lifecycle tooling: a dependents report, restore, and dry-run for `remove_entity`. Skills do not remove entities yet, so this is planned as a separate later change (`mcp-entity-lifecycle-tools`).
- Changing REST behavior or SPA-facing schemas.
- The skills that consume these tools.

## Decisions

### D1. Relationship logic moves into a published `ArchitectureRelationshipService`

A Protocol and `get_architecture_relationship_service()` accessor in `plugin-api`, implemented in core, following the `EntityService` and `FlowService` pattern. It exposes list-for-entity, create, update, and delete, takes the acting user, enforces manual-origin-only mutation and write permission on the source, and ensures tags exist. The REST controllers become thin callers; MCP controllers call the same service.

Alternatives considered:
- Call the existing REST view helpers from the MCP plugin. Rejected: views are not a contract, importing them breaks plugin boundaries, and they depend on session auth.
- Re-implement the ORM logic inside `atlas.mcp`. Rejected: violates the "services only" rule and lets two implementations drift on origin and permission rules.
- Expose the REST endpoints in the MCP OpenAPI document. Rejected: the spec forbids re-exposing the SPA-facing API.

### D2. Strict `spec` and `metadata` validation by key check in the MCP layer

Before model validation, MCP controllers compare the keys of `spec` (and `metadata`) against the target schema's declared field names and aliases. Any extra key produces a 400 listing the unknown keys and, where one is close to a valid field, a "did you mean" hint. A `relationships` key is rejected with a dedicated message naming the relationship tools. For `create_entity` this check runs against the MCP-visible field set, which excludes `relationships` even though the shared `*SpecIn` declares it.

Alternatives considered:
- Set `extra="forbid"` on the shared schemas. Rejected: ingestion constructs these schemas from manifests and the Patch schemas are also built from `*SpecIn` dumps; forbidding extras there changes ingestion and REST behavior.
- Define parallel strict subclasses per kind. Rejected: duplicates every kind's schema and drifts.
- Leave validation lenient and document it. Rejected: it is the observed failure; a skill cannot detect a silently dropped field.

This is a deliberate breaking change for callers that relied on ignored keys, called out in the proposal.

### D3. `describe_kinds` derives from the registered handlers' schemas

The tool returns, for each MCP-writable kind actually registered, the JSON Schema of its create and patch `spec` (camelCase, by alias) with enums, limits, and required fields, minus `relationships` on create. Because it reads `handler.spec_schema` and `handler.patch_schema`, enum and field changes appear without editing the tool. Kinds from optional plugins (for example `API`) appear only when installed, matching how Flow and API tools already appear.

Alternatives considered:
- A hand-maintained table of kinds and fields. Rejected: drifts from code.
- Rely on the OpenAPI body schema, where `spec` is `dict[str, Any]`. Rejected: it carries no per-kind information.

### D4. Dry-run is a request flag that runs the real code path and rolls back

`create_entity`, `update_entity`, `create_flow`, `update_flow`, and the three mutating relationship operations accept a `dryRun` boolean. When true, the service performs the operation inside a savepoint that is always rolled back, so authorization, validation, reference resolution, and constraint checks are the real ones. The response states `dryRun: true`, the resulting state, and a field-level list of changes (before and after for an update; the full new state for a create). The caller's PAT must still have the write scope, since a dry-run reveals what a write would do.

Side effects outside the database are suppressed: when `specSource` is `url`, a dry-run does not fetch the URL and reports a warning that the spec would be fetched on a real write. Audit records and any transaction-commit hooks do not fire because the transaction is rolled back.

Alternatives considered:
- Separate `preview_*` tools. Rejected: doubles the tool count and invites previews that diverge from the writes.
- A validation-only method on each service that does not touch the database. Rejected: cannot detect uniqueness conflicts or permission outcomes the real path would produce, and duplicates logic.
- Skip dry-run and rely on the client's own summary. Rejected: the summary would be a guess, not the server's answer.

### D5. `validate_flow` reuses the existing flow validation

`validate_flow` takes the same body as `create_flow` plus an optional flow id (to validate an update) and runs the same steps validation `FlowService` uses on save: reference resolution, id uniqueness, transition targets, acyclicity, mutual exclusion of the step reference fields (`entity_ref`, `external_label`, `query_ref`, `event_ref`, with `flow_ref` and `link_url` exclusive of all others), size limits. It returns all violations found, not only the first, so a client can fix a flow in one pass. It is read-only and needs the flows read scope.

Alternative: rely on `create_flow` with `dryRun`. Not enough on its own: dry-run stops at the first error and requires a target system the caller may not yet be allowed to write; `validate_flow` serves the drafting phase, dry-run serves the confirmation phase.

### D5a. `describe_kinds` stays limited to entity kinds

Flow step shape is already published: the `create_flow` and `update_flow` input schemas type every step field with a description, whereas an entity's `spec` is an untyped object in the OpenAPI document, which is why `describe_kinds` exists. Rules a schema cannot express are covered by `validate_flow`. Describing flow steps in `describe_kinds` would create a second source of truth.

### D6. Response shape for dry-run

Normal responses keep their current shape. A dry-run response is a distinct envelope with `dryRun: true`, so existing clients never see changed normal responses. In the OpenAPI document the operation's success response is therefore a union of the normal entity output and the dry-run envelope.

Alternative: a single always-wrapped envelope. Rejected: changes every existing response.

## Risks / Trade-offs

- [Strict validation breaks a client that sent extra keys] → Error names each unknown key with a hint; the change is flagged **BREAKING** in the proposal and the server instructions describe it.
- [Dry-run diverges from a real write, for example through non-transactional side effects] → Only the URL fetch is non-transactional today and is explicitly skipped with a warning; tests assert that a dry-run leaves row counts and audit records unchanged for every kind.
- [Savepoint rollback still takes locks or burns sequence values] → Acceptable for authoring volume; ids from a dry-run create are reported as null, not a real id.
- [Moving relationship logic into a service regresses REST behavior] → Existing REST tests for architecture relationships must pass unchanged; the service gets its own tests for origin and permission rules.
- [`describe_kinds` output is large] → Returned per kind, and a `kind` filter limits it to one.
- [Union response type confuses generated MCP tool output schemas] → Verify against `FastMCP.from_openapi()` output during implementation; fall back to a flat optional `dryRun` field if the union is not handled well.

## Migration Plan

1. Extract the relationship service in core with REST controllers delegating to it; ship with REST behavior unchanged.
2. Add the MCP tools and strict validation behind the existing MCP plugin; tools appear automatically after clients restart.
3. Release note for the strict-validation change.

Rollback: the new MCP operations are additive and can be dropped from the curated OpenAPI; the service extraction is behavior-preserving; strict validation can be reverted by removing the key check.

## Open Questions

None.
