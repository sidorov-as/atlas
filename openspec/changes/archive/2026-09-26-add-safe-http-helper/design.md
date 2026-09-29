## Context

Two prerelease-audit findings share one root cause — an outbound HTTP call trusts a caller- or user-supplied hostname without verifying the actual destination address is not internal/private, and does so on top of Python's `requests` library, which re-resolves DNS at connect time regardless of any earlier check a caller performed:

- `plugins/apis/backend/atlas_plugin_apis/spec_fetch.py` fetches a user-supplied `specUrl` with no IP filtering at all (SSRF).
- `plugins/auth-oidc/backend/atlas_plugin_auth_oidc/provider.py` and `plugins/auth-gitea/backend/atlas_plugin_auth_gitea/provider.py` each call `getaddrinfo()` once, then let `requests` resolve the same hostname again when it actually connects — a DNS-rebinding window between the two resolutions.

Two separate changes (`fix-apis-ssrf`, `fix-auth-dns-rebinding`) fix these call sites. This change provides the one piece of logic both of them need — "resolve once, verify the address, connect pinned to it" — as shared infrastructure in `plugin-api/python/atlas_plugin_api`, the contract package every backend plugin already imports (confirmed by scanning its flat module layout: `auth.py`, `catalog.py`, `permissions.py`, etc., each a focused, independently-importable module with explicit exports from `__init__.py`).

## Goals / Non-Goals

**Goals:**
- One reviewed, unit-tested implementation of "safe outbound HTTP fetch" that both dependent changes can call instead of each writing their own SSRF guard.
- An API shape general enough to serve both consumers: `spec_fetch.py` needs streaming + a byte cap (fetching a possibly-large spec document); the auth providers need a simpler bounded request/response (token exchange, userinfo).
- Defense that survives redirects and DNS rebinding, not just a check on the original URL.

**Non-Goals:**
- Implementing the call-site changes in `spec_fetch.py` or either auth provider — that's `fix-apis-ssrf` and `fix-auth-dns-rebinding`'s job.
- A general-purpose HTTP client abstraction or `requests.Session` replacement — this is a narrowly-scoped safety primitive, not a new house HTTP library.
- Deciding policy questions that belong to the consumers (e.g. whether `spec_fetch.py` allows an operator allowlist for non-HTTPS URLs) — the helper exposes the knobs; each consumer decides how to set them.

## Decisions

- **Home: `plugin-api/python/atlas_plugin_api/safe_http.py`.** Alternative considered: putting it in `core/backend` and having plugins import from Core — rejected, since the existing architecture (per `plugin-contract-packages`/`core-plugin-contract-surface` specs) is that plugins depend on `atlas_plugin_api`, not on Core internals, and both consumers here are plugins (`apis`, `auth-oidc`, `auth-gitea`).
- **Resolve-then-pin, not a DNS allowlist.** The helper resolves the hostname via the stdlib resolver, filters the resulting addresses, and then makes the actual connection to a specific verified IP (passing the original hostname as `Host`/SNI) — rather than trying to block "bad" hostnames by name/pattern, which doesn't defend against rebinding at all.
- **IP-range rejection covers:** RFC1918 (10/8, 172.16/12, 192.168/16), loopback (127/8, `::1`), link-local (169.254/16, `fe80::/10`), multicast, IPv6 unique-local (`fc00::/7`), and other IANA-reserved ranges. Cloud metadata endpoints (e.g. `169.254.169.254`) are covered by the link-local rejection, not a separate special case.
- **Redirects: re-validate every hop, don't just disable them.** Alternative considered: `allow_redirects=False` unconditionally — rejected as the default because `spec_fetch.py`'s current legitimate use case (fetching a spec document) plausibly needs to follow a redirect from a real external host. Instead, the helper performs the full resolve-and-verify step again for each redirect target before following it, capped at a small fixed number of hops. A caller that wants zero redirects can pass `max_redirects=0`.
- **Byte-cap via streaming, not via `Content-Length` trust.** `Content-Length` is attacker-controlled and can be absent or wrong; the helper reads the response body incrementally and aborts once the cap is exceeded, regardless of what the header claims.
- **HTTPS-only by default, explicit opt-in for HTTP.** Matches the SSRF finding's own recommended fix shape ("allow only HTTPS, optionally an operator allowlist"). The opt-in is a caller-supplied flag, not a global setting, so `fix-auth-dns-rebinding` (which may need HTTP against a self-hosted Gitea instance in some deployments) can make that call independently of `fix-apis-ssrf`'s policy.
- **Sequencing: this change lands before its two consumers.** OpenSpec's `spec-driven` schema has no formal cross-change dependency field (verified by inspecting `openspec status`/`instructions` output — dependencies are only tracked between artifacts *within* one change). The ordering is therefore a coordination note in each change's proposal/design, not a tool-enforced gate; whoever applies `fix-apis-ssrf` or `fix-auth-dns-rebinding` needs to check this change has actually landed first.

## Risks / Trade-offs

- **A shared helper becomes a single point of failure for two different security fixes** → mitigated by shipping this change with its own dedicated unit tests (loopback, RFC1918, IPv6 loopback/ULA, link-local/metadata address, redirect-to-disallowed-address, a simulated DNS-rebinding scenario) independent of and before either consumer exists, so the primitive is proven correct on its own.
- **API design done before either real caller exists, so it may not fit either one cleanly** → flagged as an explicit open question below; the two consumer changes were written in parallel against this design and one of them (`fix-auth-dns-rebinding`) already flagged a fit concern with Gitea's allauth-managed `requests.Session` — worth resolving before implementation starts.
- **Resolve-then-pin against an IP can break TLS certificate validation if not done carefully** (many `requests`/`urllib3` setups validate the cert against the connected IP unless SNI/hostname are threaded through correctly) → the implementation must use an HTTPAdapter/transport-level override that connects to the verified IP while still presenting and validating the original hostname for TLS, not a raw socket swap. This is a real implementation risk worth a spike before committing to a specific `requests` integration approach.

## Open Questions

- Does the chosen connect-to-verified-IP mechanism compose with `django-allauth`'s internally-managed `requests.Session` inside the Gitea OAuth2 provider, or does `fix-auth-dns-rebinding` need a different integration point (e.g. a custom `requests.adapters.HTTPAdapter` registered on that session) than the one `fix-apis-ssrf` uses directly? Resolve during `fix-auth-dns-rebinding`'s implementation, but the answer may require revisiting this helper's API.
- Exact IPv6 reserved-range list to exclude (beyond loopback/ULA/link-local) — should be finalized against the current IANA IPv6 special-purpose registry at implementation time rather than hardcoded from this design doc, since the registry is occasionally amended.
