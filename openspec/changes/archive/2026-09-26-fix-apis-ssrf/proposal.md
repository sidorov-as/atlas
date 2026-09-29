## Why

A prerelease security audit found that resolving a user-supplied `specUrl` for an API entity is an unguarded Server-Side Request Forgery vector: `atlas_plugin_apis.spec_fetch.fetch_spec_content` calls `requests.get(url)` with no private/loopback/link-local IP filtering, no allowlist, redirects followed by default, no response size cap, and no streaming. Any user able to create or edit an API entity can make the backend reach internal services or cloud metadata endpoints, or force it to download an unbounded response. This is a release blocker (OWASP A10 SSRF, A04 Insecure Design).

## What Changes

- `fetch_spec_content` (`plugins/apis/backend/atlas_plugin_apis/spec_fetch.py`) validates and fetches `spec_url` using the shared SSRF-safe fetch helper from `add-safe-http-helper` (a separate, parallel change) instead of a bare `requests.get`: HTTPS-only by default, no credentials/fragments in the URL, DNS resolved once and connected to the verified (non-private/loopback/link-local/reserved) IP, redirects re-validated per hop, and the response streamed with a hard byte-size cap.
- The YAML/JSON parse step gains a size and nesting-depth limit, not just a "did it parse" check, so a small URL cannot still trigger a YAML-bomb-style expansion.
- Both existing call sites — `ApiDetails.apply_api_spec_source` (CRUD create/patch, invoked synchronously in the request path) and `atlas_plugin_apis.extension_points.due_for_spec_refresh` (the ingestor's periodic poll) — keep working synchronously for now; the fetch stays bounded by a tight timeout and the new byte cap rather than being moved to a background worker in this change (see design.md Decisions for why full async offload is deferred).
- **BREAKING** (operational, not API-contract): if a deployment's spec-hosting endpoint responds only over HTTP, or resolves to a private/internal address (e.g. an internal Git/artifact server used intentionally), it will start failing to resolve until the operator adds it to the new allowlist. This is the intended effect of closing the SSRF hole.
- Tests added for `127.0.0.1`, IPv6 loopback, RFC1918 ranges, redirect chains to disallowed addresses, and DNS rebinding between validation and connection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `api-spec-documents`: "Setting a spec URL resolves it immediately" and "Periodic refresh of URL-sourced specs" both currently describe fetching `spec_url` with no safety constraints on the target address, redirect behavior, or response size. These requirements are updated to state that resolution only ever fetches HTTPS URLs (or an operator-allowlisted exception), only ever connects to a publicly-routable, non-reserved address, and always applies a response size cap — with a fetch that is rejected under any of these conditions treated the same as any other failed resolution (`spec_resolve_failed` set, existing `spec_content` left untouched).

## Impact

- `plugins/apis/backend/atlas_plugin_apis/spec_fetch.py`: fetch logic rewritten to use the shared safe-fetch helper.
- `plugins/apis/backend/atlas_plugin_apis/extension_points.py`, `plugins/apis/backend/atlas_plugin_apis/api/views.py` (or wherever `apply_api_spec_source` is invoked from the CRUD request path): no call-site signature change expected, but request latency for `spec_source=url` creates/updates may change slightly under the new stricter timeout/size-cap behavior.
- Depends on `add-safe-http-helper` (separate change, proposed in parallel) landing first — see design.md.
- Operators with `specUrl`s pointing at non-HTTPS or non-public-routable hosts need a new allowlist entry (see design.md Migration Plan) — worth a release note.
