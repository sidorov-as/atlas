## 1. Shared schema write function (database-schema)

- [x] 1.1 Extract one function that saves dialect and SQL, parses, sets `parse_status`, and returns `(parse_status, parse_error)`; switch `views._apply_source` and `facet_writer.apply` to it
- [x] 1.2 Move the YAML-managed guard and `resource.edit` check into a shared helper used by the CRUD view and the new paths
- [x] 1.3 Tests: failed parse returns the parser message, successful parse has an empty error, CRUD and ingestion store identical state

## 2. Ticket core

- [x] 2.1 Add the `UploadTicket` model and migration (token hash, entity, field, params, issuing user and PAT, expiry, size limit, consumed-at, created-at)
- [x] 2.2 Add the upload target registry and adapter protocol to `atlas_plugin_api` (keyed by `(kind, field)`, declares required scope and size limit, typed validation error)
- [x] 2.3 Implement ticket issuance: permission and scope check, YAML-managed rejection, parameter validation, token generation, hashed storage, TTL setting
- [x] 2.4 Implement the public `PUT` route: lookup by hash, identical 404s for unknown/expired/consumed/revoked, issuing PAT and owner-active check, size cap on bytes read, adapter call as the issuing user
- [x] 2.5 Consume the ticket atomically with a successful write (conditional update); leave it unconsumed on validation, permission, and size failures
- [x] 2.6 Return `{ok, summary}` on success and an error body with the reason on rejection
- [x] 2.7 Keep the token out of logs (route/path logging configuration)
- [x] 2.8 Delete expired and consumed tickets after a retention period (done on ticket issuance, not as a scheduled job: a job declared by always-on Core makes every startup read the job store)
- [x] 2.9 Tests: issue, upload, retry after failure, second upload, expiry, concurrent uploads, permission lost, oversize body, unknown target, revoked PAT, inactive owner

## 3. PAT integration

- [x] 3.1 Invalidate unused tickets when their issuing PAT is revoked or expired or the owner is deactivated (check at use time)
- [x] 3.2 Tests: revoked PAT's ticket rejected, another PAT's ticket unaffected

## 4. API spec adapter (apis)

- [x] 4.1 Register `(api, spec)` with the required scope `apis:write` and the 20 MB limit
- [x] 4.2 Adapter: apply the body through the existing spec source application, run endpoint/operation synchronization, set the source to inline content, return spec kind and counts
- [x] 4.3 Tests: valid OpenAPI, valid AsyncAPI, empty body, over parse limits (stored spec unchanged), source switched from `url`

## 5. Database schema adapter and MCP write

- [x] 5.1 Register `(resource, schema)` with required scope `catalog:write`; validate the dialect parameter at request time
- [x] 5.2 Adapter: create or replace the Facet through the shared function; return `parse_status`, `parse_error`, and table count
- [x] 5.3 Add the `set_resource_schema` MCP operation (PAT, scope, strict keys, `dryRun`), present only with `atlas.database-schema`
- [x] 5.4 Tests: create, replace, unparseable upload saved with the reason, dry-run persists nothing, YAML-managed rejected, absent without the plugin

## 6. MCP request operation and server layer

- [x] 6.1 Add the `request_attach` operation to the curated MCP API (entity as `kind:name`, field, params), present only when a target is registered
- [x] 6.2 Add the hand-written wrapper in `mcp/atlas_mcp/server.py` that builds the full URL from `ATLAS_API_URL` and returns expiry, size limit, and an example upload command
- [x] 6.3 Document the container host caveat in the tool result and `mcp/README.md`
- [x] 6.4 Update the server instructions: when to upload, when to use inline, when to ask the user; `ok` means saved for schemas
- [x] 6.5 Tests: MCP OpenAPI document contents with and without the plugins, full URL composition, scope enforcement

## 7. Docs and skills

- [x] 7.1 Update the Atlas skills that describe attaching specs or schemas to prefer the upload link for large files
- [x] 7.2 Add a short section to the MCP documentation describing the upload flow and the security properties of tickets

## 8. Verification

- [x] 8.1 End-to-end check: create an API without a spec, request a ticket, upload a multi-megabyte spec with `curl`, confirm endpoints appear
- [x] 8.2 End-to-end check: the same for a Resource schema, including a deliberately broken SQL file
- [x] 8.3 Confirm no log line contains a ticket token during the end-to-end runs
- [x] 8.4 Run the full backend and MCP test suites and `openspec validate mcp-upload-links`
