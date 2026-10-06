## Context

Attaching an API spec or a database schema through MCP today means passing the whole text as a tool argument (`spec_content` on `create_entity`/`update_entity`); the Resource database schema has no MCP path at all, because its Facet endpoint accepts only session auth. Large files therefore either burn LLM context or push the agent to read `ATLAS_API_URL` and the PAT from its environment and call the main API directly, bypassing the curated MCP surface.

Relevant current structure:

- API spec content is applied by `apply_api_spec_source` in the APIs plugin, which enforces size, depth, and node limits and rejects unusable bodies; the same function serves the CRUD API and ingestion.
- The database schema is a Facet (`DatabaseSchema`, one-to-one with the entity). Its CRUD controller and the ingestion facet writer each contain their own "save SQL, try to parse, record `parse_status`" logic. A failed parse is saved, and the parser's message is discarded.
- Personal Access Tokens live in core. Plugins reach shared behavior through the `atlas_plugin_api` package and keyed extension points.
- The MCP server turns the curated MCP OpenAPI document into tools with `FastMCP.from_openapi`, with a few hand-written tools. It knows the Atlas base URL (`ATLAS_API_URL`).

## Goals / Non-Goals

**Goals:**
- Let an agent with a shell upload a large file directly to Atlas without routing it through the LLM and without holding the PAT.
- One mechanism for any plugin-owned field (first adopters: API spec, resource schema).
- Preserve the existing write rules (RBAC, scopes, YAML-managed guard, limits) on the new path.
- Return actionable validation messages to the agent.
- Keep inline content as a fallback.

**Non-Goals:**
- Downloading specs or schemas through links.
- Staging storage, multi-target or bulk uploads, object storage.
- Changing how URL-sourced specs (`spec_url`) are fetched.
- Dry-run for the raw upload (validation outcome in the response is enough).

## Decisions

### D1. Direct apply, no staging
The `PUT` body is handed to the target adapter, which writes it into the real field (`spec_content`, `DatabaseSchema.source_sql`). No staged blob table.

- Alternative: upload to a staging row, then attach by id in a second MCP call. Needs TTL cleanup, a second round trip, and a place for validation errors to surface later. It only pays off for one file shared by several targets, which is not a requirement.
- Consequence: the entity must exist before a ticket can be requested. Entities without a spec are already a valid state, so the agent creates the entity first and then requests the ticket.

### D2. Ticket model and placement
A `UploadTicket` model in core, next to the PAT model, with: token hash, entity, field, JSON params, issuing user, issuing PAT, expiry, size limit, consumed-at, created-at. The registry and the adapter protocol live in `atlas_plugin_api`, so the APIs and database-schema plugins can register targets without importing core internals. The public `PUT` route lives in core. The request operation lives in the MCP plugin, because it is a PAT-authenticated, scope-checked operation of the curated surface.

- Alternative: put everything in the MCP plugin. Then core would not be able to serve the unauthenticated `PUT` without a dependency on an optional plugin, and the ticket would not be reusable by the UI later.

### D3. Token: opaque, hashed, in the path
`secrets.token_urlsafe(32)`, stored as SHA-256 (the token is high entropy, so a fast hash is enough). The token is a path segment of the `PUT` URL (`/api/uploads/<token>`), not a query parameter, and the route is excluded from request logging of the path parameter. Responses to unknown, expired, consumed, and revoked tickets are identical `404`s, so a prober learns nothing.

- Alternative: signed token (JWT-like) with no table. Rejected: single-use and revocation both need server state anyway.

### D4. Auth: the URL is the credential; the issuing PAT is checked as state
The `PUT` has no `Authorization` header. On each `PUT` Atlas loads the ticket by hash and checks, in order: not expired, not consumed, issuing PAT still valid (not revoked, not expired), owner active, and then runs the write as the issuing user with the target's normal permission check. A lost permission fails the write without consuming the ticket.

- Rejected: requiring the PAT on the `PUT` too. It would put the PAT back into the agent's shell, which is exactly what this change avoids.

### D5. Consume only on success, atomically
The ticket is marked consumed in the same transaction as the successful adapter write, with a conditional update (`consumed_at IS NULL`) so concurrent uploads cannot both succeed. Validation failures, permission failures, and oversize bodies leave the ticket unconsumed, so the agent can retry the corrected file on the same URL until expiry. Default TTL 10 minutes, configurable.

### D6. Size limit enforced before reading the body
The limit is set per target (APIs: the existing spec limit of 20 MB; schema: a smaller default, configurable) and stored on the ticket. The endpoint checks `Content-Length` and also caps the bytes actually read, so a missing or false header cannot bypass it. Django's global request-size setting is raised only for this route or handled by reading the stream directly.

### D7. Adapter contract
`apply(entity, body: bytes, params: dict, user) -> UploadResult(summary: dict)`; validation problems raise a typed error carrying the reason, which the endpoint maps to an error response with the message in the body. Adapters call the same functions as the regular write paths:

- API `spec`: the existing spec source application, then the same endpoint/operation synchronization. Summary: spec kind and counts. Sets the spec source to inline content, as writing `spec_content` does.
- Resource `schema`: the shared schema write function (D8). Params carry the dialect, validated at request time. Summary: `parse_status`, `parse_error`, table count.

### D8. One schema write function, and `parse_error`
Extract the "save SQL, parse, record status" logic from the CRUD view and the ingestion facet writer into one function in the database-schema plugin that returns `(parse_status, parse_error)`. It also owns the permission check (YAML-managed guard and `resource.edit`) so the CRUD endpoint, the MCP write, and the upload adapter cannot diverge. A failed parse still saves the SQL; `ok` means saved, and the parse outcome is reported separately. Whether to persist `parse_error` on the Facet (migration, UI display) is left out: the message is returned to the caller only.

### D9. Schema access for MCP
The Facet endpoint stays session-only. The MCP plugin adds `set_resource_schema` as its own curated operation (PAT, scope-checked, `dryRun` supported, strict keys) that calls the shared function. The write scope for both `request_attach` and `set_resource_schema` on a schema is `catalog:write`; for an API spec it is `apis:write`. Each adapter declares the scope it requires, and `request_attach` checks it.

### D10. MCP surface and URL composition
`request_attach(entity, field, params)` is generated from the curated OpenAPI like other operations and returns a relative upload path plus metadata. A small hand-written layer in the MCP server turns it into the tool result the agent sees: a full URL from `ATLAS_API_URL`, expiry, size limit, and an example `curl -T file URL` command. The Atlas server therefore needs no public base URL setting.

- Docker caveat: when the MCP server runs in a container, `ATLAS_API_URL` may be a container-only host (such as `host.docker.internal`) that the agent's shell cannot resolve. The tool result and instructions say so and tell the agent to substitute a reachable host.

### D11. Choosing between paths
Instructions in the server describe three cases: shell available and file large or on disk, so use `request_attach`; small content or no shell, so use inline (`spec_content`, `set_resource_schema`); neither works, so ask the user. The decision is left to the agent.

## Risks / Trade-offs

- [New unauthenticated write route] → 256-bit tokens, hashed storage, short TTL, single use, per-target scope and size cap, identical 404s, no token in logs, issuer's PAT validity re-checked on every use.
- [URL leaks via shell history or agent transcripts] → TTL and single use bound the exposure; the scope of one ticket is one field of one entity; the PAT itself is never shown.
- [Large body parsed inside the request] → same limits as `create_entity` with a spec today (size, depth, nodes); request timeout to be checked against the largest allowed spec during implementation.
- [Entity must exist before the ticket] → the agent creates it without a spec first; the spec-less state already exists.
- [`ok` ambiguity for schemas] → response and tool descriptions state `ok` means saved; `parse_status`/`parse_error` carry the parse outcome.
- [Docker URL mismatch] → documented in the tool result and README.
- [Third copy of write logic] → avoided by D8; a test asserts all paths produce identical stored state.

## Migration Plan

1. Add the ticket model and migration (new table only; no existing data touched).
2. Land the shared schema write function with the CRUD view and ingestion writer switched over, behavior unchanged except for the new `parse_error` value.
3. Add the registry, the endpoint, and the two adapters, then the MCP operations and the server wrapper and instructions.
4. Rollback: remove the route and MCP operations; the table can stay empty. No existing behavior depends on the new pieces.

## Open Questions

- Should `parse_error` be persisted on the Facet so the UI can show it too? Proposed as a follow-up.
- Ticket TTL and the schema size limit defaults: 10 minutes and a value to be set during implementation from real schema sizes.
