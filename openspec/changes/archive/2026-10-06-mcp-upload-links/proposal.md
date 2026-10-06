## Why

An agent that needs to attach a large artifact to the catalog (an API spec, a database schema) has only one MCP path: pass the full text as a tool argument, which means routing megabytes through the LLM context. In practice agents notice this is impractical and work around it by reading `ATLAS_API_URL` and the PAT from the environment and calling the main API directly. That bypasses the curated MCP surface (strict keys, write preview, scoped operations) and puts the PAT into the agent's shell.

Agents that have a shell should be able to upload the file themselves, with a narrowly scoped, short-lived link, without ever handling the PAT.

## What Changes

- Add **upload tickets**: a caller with write permission on an entity requests a ticket for one `(entity, field)` target and receives a single-use, time-limited, unguessable upload URL. A `PUT` of the raw file body to that URL applies it directly to the target; there is no intermediate staging storage.
- The `PUT` needs no `Authorization` header. The URL token is the credential, bound to the entity, the field, the issuing user, and the issuing PAT; revoking or expiring that PAT invalidates its unused tickets.
- Upload targets are registered by plugins as `(kind, field)` with an adapter that receives the body bytes and ticket parameters and returns a summary. Two adapters ship with this change:
  - API `spec` (reuses the existing spec source application and its size and parse limits).
  - Resource database schema (Facet), with the SQL dialect fixed at ticket time.
- The `PUT` response has a common shape `{ok, summary}`; each adapter fills `summary`. Validation failures return a normal error with the reason in the body.
- Database schema writes report the parse failure reason: the Facet keeps saving the SQL on a failed parse, and the response carries `parse_status` and `parse_error` with the parser's message.
- Add MCP tools: `request_attach` (returns the upload target as a path-bearing result that the MCP layer turns into a full URL from its configured Atlas base URL) and `set_resource_schema` (inline fallback for schemas, mirroring `spec_content` for APIs). Inline `spec_content` stays as the fallback for clients without a shell; the agent decides between uploading itself and asking the user.
- Server instructions tell the agent when to prefer the upload link (shell available, large file) and when inline is acceptable.
- The Resource database schema write path becomes reachable with a PAT through the MCP API and shares one write function with ingestion, removing the duplicated "save and parse" logic.

Out of scope: downloading specs or schemas through links, staging or multi-target uploads, bulk operations, object storage.

## Capabilities

### New Capabilities
- `upload-tickets`: issuing, storing (hashed), validating, consuming, and revoking single-use upload tickets; the unauthenticated `PUT` endpoint; the plugin-registered upload target registry and adapter contract; the `{ok, summary}` response.
- `mcp-upload-tools`: the `request_attach` and `set_resource_schema` MCP tools, URL composition on the MCP side, and the agent-facing instructions for choosing between upload and inline.

### Modified Capabilities
- `database-schema-plugin`: write path usable with a PAT and through MCP; one shared write function; parse failure reason returned to the caller.
- `apis-plugin`: registers the API `spec` upload target and its adapter.
- `personal-access-tokens`: revoking or expiring a PAT invalidates unused upload tickets it issued.
- `mcp-plugin`: the curated MCP API gains the ticket request operation and the schema write operation.

## Impact

- `plugins/mcp`: new views and schemas for ticket requests and the schema write; `mcp/atlas_mcp/server.py` gains a hand-written wrapper for `request_attach` and updated instructions.
- `plugins/apis`, `plugins/database-schema`: upload target adapters; `database-schema` extracts a shared write function used by its API view, the ingestion facet writer, and the adapter.
- Core/plugin API package: ticket model and migration, target registry extension point, public `PUT` route excluded from session/PAT auth.
- `personal-access-tokens`: revocation hook for tickets.
- Security-relevant: new unauthenticated write route gated only by an unguessable token. Mitigations are required by the specs (hashed storage, TTL, single use, size cap, per-target scope, no token in logs).
