## Why

A prerelease security audit found two independent outbound-HTTP call sites with the same underlying gap — the code resolves or trusts a hostname without verifying the destination isn't an internal/private address, and (for one of them) lets the HTTP client re-resolve DNS a second time after an initial "safe" check:

- SSRF via `specUrl` in `plugins/apis/backend/atlas_plugin_apis/spec_fetch.py:26` (`fix-apis-ssrf`, a separate proposed change).
- DNS rebinding in the OIDC and Gitea auth providers, which call `getaddrinfo()` themselves and then let `requests` independently re-resolve the same hostname when it connects (`fix-auth-dns-rebinding`, a separate proposed change).

Fixing these independently means writing "resolve DNS, reject private/loopback/link-local/reserved ranges, connect pinned to the verified IP" twice, in two plugins, with no shared test coverage. This change adds that logic once, as a shared helper in `plugin-api/python/atlas_plugin_api` — the contract package every backend plugin already depends on — so both dependent changes consume one reviewed implementation instead of two hand-rolled guards.

## What Changes

- Add a new module, `atlas_plugin_api.safe_http`, providing a small SSRF-safe HTTP-fetch API: resolve a target hostname's DNS once, reject any resolved address in a private/loopback/link-local/multicast/reserved range, connect to the verified IP directly while preserving the correct `Host` header and TLS SNI, and either disable HTTP redirects by default or fully re-validate each redirect hop before following it.
- Support streaming reads with a caller-supplied byte cap, for callers (like spec fetching) that also need to bound response size.
- Reject URLs containing embedded credentials (`user:pass@host`) or a fragment.
- Default to HTTPS only, with an explicit opt-in for callers that need HTTP (e.g. an operator-configured allowlist scenario) rather than a global default.
- Export the new symbols from `atlas_plugin_api/__init__.py` following the package's existing flat-module/explicit-export convention.
- This change does **not** touch either call site — `spec_fetch.py` and the OIDC/Gitea providers are updated by `fix-apis-ssrf` and `fix-auth-dns-rebinding` respectively, which both depend on this change landing first.

## Capabilities

### New Capabilities

- `ssrf-safe-fetching`: A shared, reusable primitive for making outbound HTTP requests to operator- or user-supplied URLs/hostnames without exposing the backend to SSRF or DNS-rebinding — DNS resolved once, private/loopback/link-local/reserved destinations rejected, connection pinned to the verified address, redirects re-validated or disabled, response size bounded.

### Modified Capabilities

None — no existing capability describes outbound-fetch safety; this is genuinely new shared infrastructure, not a change to a capability's existing behavior.

## Impact

- New file(s) under `plugin-api/python/atlas_plugin_api/` (a `safe_http` module) plus an export addition to `atlas_plugin_api/__init__.py`.
- New dependency for two other proposed changes: `fix-apis-ssrf` and `fix-auth-dns-rebinding` both specify using this helper rather than reinventing the guard logic, and should land after this change (this schema has no formal cross-change dependency field; the ordering is a coordination note, not an enforced gate).
- No behavior change to any existing call site in this change itself — it only adds new, unused-until-consumed code to `plugin-api/python`.
- Test-only impact elsewhere: this change should ship its own unit tests (loopback, RFC1918, IPv6 loopback/ULA, redirect-to-disallowed, DNS-rebinding simulation) independent of the two consumers, so the primitive is verified before anything depends on it.
