## Context

`RequestsOIDCTransport` (`plugins/auth-oidc/backend/atlas_plugin_auth_oidc/provider.py`) and `AllauthGiteaTransport` (`plugins/auth-gitea/backend/atlas_plugin_auth_gitea/provider.py`) are near-identical in structure: both implement `_validate_resolved_destination(url)`, which does its own `socket.getaddrinfo` and rejects link-local/multicast/reserved addresses, gates loopback behind `allow_development_http`, and requires private addresses to be in `allowed_destinations`. Both then call the validated `url` string through a normal HTTP client (`requests.get`/`.post` for OIDC; an allauth-managed `requests` session for Gitea), which performs its own independent DNS resolution when it actually opens the connection. Two resolutions of the same hostname, separated by network I/O time, is exactly the DNS-rebinding window: an attacker who controls the DNS answer for the configured issuer/instance hostname can serve a safe address for the validation lookup and a private/internal address moments later for the real connection.

A separate, parallel change (`add-safe-http-helper`) is adding a shared primitive to `plugin-api/python/atlas_plugin_api/` for exactly this "resolve once, verify, connect pinned to the verified address" pattern, intended to also be used by the SSRF fix for `specUrl` fetching (`fix-apis-ssrf`). This change is the second consumer of that primitive.

## Goals / Non-Goals

**Goals:**
- Close the gap between "address was validated" and "address is used" in both providers' outbound HTTP calls, so no request can connect to an address different from the one `_validate_resolved_destination` approved.
- Preserve the correct `Host` header and TLS SNI for the configured hostname, so certificate validation and any hostname-based routing on the issuer/instance side keeps working exactly as today.
- Keep the existing address-class policy (link-local/multicast/reserved rejection, loopback dev-gate, private-address allowlist) unchanged — only the connection step changes.
- Reuse the shared helper from `add-safe-http-helper` instead of writing separate pinning logic in each provider.

**Non-Goals:**
- Changing OIDC/OAuth protocol validation (PKCE, state, nonce, issuer/audience, signature checks) — already correct and out of scope.
- Changing the address-class policy itself (what counts as allowed private/loopback) — that's existing, deliberate provider configuration (`allowed_destinations`, `allow_development_http`), not something this change revisits.
- Building the shared helper itself — that's `add-safe-http-helper`'s scope; this change only consumes it.
- Redirect handling — both transports already call with `allow_redirects=False`, so there is no redirect-revalidation gap to close here.

## Decisions

- **Consume the shared helper rather than hand-rolling pinning twice.** OIDC and Gitea currently duplicate `_validate_resolved_destination` near-verbatim; a third near-duplicate of "connect to a specific IP while keeping Host/SNI correct" would be a third copy of subtle, security-relevant socket/TLS code. The shared helper from `add-safe-http-helper` is the right place for this once, reused by both providers and by `fix-apis-ssrf`.
- **Provider-specific address-class policy stays in the providers.** The shared helper is a low-level transport primitive (resolve, verify not-prohibited by generic rules, connect pinned). The OIDC/Gitea-specific policy — the `allowed_destinations` allowlist and `allow_development_http` opt-in, which are per-provider configuration, not global policy — stays as a layer each provider applies on top of (or supplies as a predicate/callback into) the shared helper's resolution step, rather than being pushed down into the shared helper itself.
- **Gitea's allauth-managed session is a constraint on the implementation, not the design.** `AllauthGiteaTransport._session()` returns a session from `allauth.socialaccount.adapter.get_adapter().get_requests_session()`, which this change does not want to fully bypass (it's deliberately using allauth's maintained session integration per the existing code comment). The implementation needs to pin the connection (e.g. via a custom transport adapter mounted on that session, or by resolving to a specific IP and setting the appropriate low-level connection parameters) without discarding the allauth session wrapper. This is left to the implementation to work out against whatever API `add-safe-http-helper` settles on; if the helper's API can't be composed with an existing `requests.Session`, that's a finding to raise against `add-safe-http-helper`'s design before this change is implemented.

## Risks / Trade-offs

- **Implementation depends on another in-flight change's API.** If `add-safe-http-helper`'s helper shape doesn't compose cleanly with Gitea's allauth-session requirement, this change's implementation may need to request an adjustment to that helper rather than build a workaround here. Mitigation: flag this explicitly during `add-safe-http-helper`'s review, before this change starts implementation.
- **IP-pinning with correct SNI is easy to get subtly wrong** (e.g. connecting by IP but forgetting to force SNI to the original hostname breaks TLS entirely, or a naive implementation reintroduces a resolve-then-reconnect gap under connection pooling/keep-alive reuse). Mitigation: test against a real TLS endpoint reachable by both hostname and pinned IP, and add a test that asserts the transport does not re-resolve DNS between validation and connection (e.g. by mocking the resolver and asserting it is called exactly once per request).
- **Low likelihood, since it requires an attacker who can control authoritative DNS for the configured issuer/instance hostname** — this is a defense-in-depth fix, not a response to an observed exploit. Scoped accordingly: transport-layer only, no broader rework.

## Migration Plan

1. Land `add-safe-http-helper` first.
2. Adopt the helper in `RequestsOIDCTransport.get_json`/`.post_form`.
3. Adopt the helper in `AllauthGiteaTransport.get_profile`/`.get_health`/`.exchange_code`, resolving the allauth-session composition question from Decisions above.
4. Add a regression test per provider asserting exactly one DNS resolution occurs per outbound call.
5. No rollback complexity: purely additive transport hardening, no data or config migration.

## Open Questions

- Does `add-safe-http-helper`'s eventual API compose with an existing `requests.Session` (needed for Gitea's allauth-managed session), or does it assume owning the full request lifecycle? Needs resolving during that change's design review, before this change is implemented.
