## 1. Prerequisite

- [x] 1.1 Confirm `add-safe-http-helper` has landed (or its interface is stable enough to code against) before starting implementation.

## 2. Safe fetch integration

- [x] 2.1 Rewrite `fetch_spec_content` in `plugins/apis/backend/atlas_plugin_apis/spec_fetch.py` to use the shared safe-fetch helper instead of bare `requests.get`.
- [x] 2.2 Enforce HTTPS-only by default; wire in an operator-configurable allowlist for non-HTTPS or otherwise-exempted hosts.
- [x] 2.3 Reject URLs containing credentials or a fragment.
- [x] 2.4 Stream the response with a hard byte-size cap; abort and treat as failed resolution if exceeded.
- [x] 2.5 Add YAML/JSON parse size and nesting-depth limits (not just success/failure of `yaml.safe_load`).

## 3. Behavior preservation

- [x] 3.1 Confirm `apply_api_spec_source` (CRUD create/patch path) and `due_for_spec_refresh` (ingestor periodic refresh) both continue to treat a rejected/unsafe fetch identically to today's "fetch failed" path (`spec_resolve_failed = True`, `spec_content` untouched).
- [x] 3.2 Confirm request latency under the new timeout/size-cap behavior is acceptable for the synchronous CRUD save path.

## 4. Allowlist mechanism

- [x] 4.1 Implement operator-configurable allowlist (env var or settings-based) for HTTP and/or otherwise-reserved-address exceptions.
- [x] 4.2 Document the allowlist mechanism and default (empty/deny) in operator-facing docs.

## 5. Tests

- [x] 5.1 `127.0.0.1` and other IPv4 loopback/link-local addresses are rejected.
- [x] 5.2 IPv6 loopback (`::1`) and link-local addresses are rejected.
- [x] 5.3 RFC1918 private ranges are rejected.
- [x] 5.4 A redirect chain ending at a disallowed address is rejected, not silently stopped at the last good hop.
- [x] 5.5 DNS rebinding between validation and connection does not bypass the address check.
- [x] 5.6 An oversized response is aborted via the byte cap rather than fully buffered.
- [x] 5.7 A deeply nested / oversized YAML body is rejected by the parse limit.
- [x] 5.8 A legitimate HTTPS spec URL still resolves successfully (no false-positive regression).
- [x] 5.9 An allowlisted non-HTTPS/internal host resolves successfully when explicitly configured.

## 6. Release notes

- [x] 6.1 Document the behavior change (HTTPS-only default, address restrictions) as a release note, since it can turn a previously-working `specUrl` into a failed resolution for some deployments.
