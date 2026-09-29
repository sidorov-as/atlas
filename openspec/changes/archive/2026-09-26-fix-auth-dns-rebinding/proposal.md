## Why

The built-in OIDC and Gitea authentication providers already validate the resolved IP address of every outbound request before making it (`_validate_resolved_destination` in both `RequestsOIDCTransport` and `AllauthGiteaTransport`: rejects link-local/multicast/reserved addresses, gates loopback behind a development opt-in, and requires private addresses to be explicitly allowlisted). But that validation and the actual request are two separate DNS resolutions: `_validate_resolved_destination` calls `socket.getaddrinfo` itself, then `requests`/the allauth session independently re-resolves the same hostname when it connects. An attacker controlling DNS for the configured issuer/instance hostname can return a safe address for the validation lookup and a private/internal address for the connection a moment later (DNS rebinding), bypassing the validation entirely.

## What Changes

- Both providers' transports connect using the already-resolved, already-validated IP address directly, instead of letting the HTTP client re-resolve the hostname a second time.
- The `Host` header and TLS SNI continue to use the original configured hostname, so certificate validation and virtual-hosted issuers/instances keep working.
- No change to the existing address-class policy itself (link-local/multicast/reserved rejection, loopback dev-gate, private-address allowlist) — this closes the gap between validating an address and using it, not the validation rules.
- Depends on `add-safe-http-helper` (a separate, parallel change proposing a shared "resolve once, connect pinned to the verified IP" primitive in `plugin-api/python/atlas_plugin_api/`): this change adopts that primitive in place of each provider's current "validate, then let the client re-resolve" pattern, rather than hand-rolling IP-pinning logic twice. If `add-safe-http-helper` has not landed yet when this change is implemented, that dependency must be resolved first.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `authentication-provider-sdk`: adds a new requirement that built-in redirect-flow providers' outbound requests are resistant to DNS rebinding (connect pinned to the already-validated resolved address), alongside the existing "OAuth and OIDC adapters meet a testable protocol baseline" requirement which this complements at the transport layer.

## Impact

- `plugins/auth-oidc/backend/atlas_plugin_auth_oidc/provider.py`: `RequestsOIDCTransport.get_json` and `.post_form` (token endpoint, userinfo endpoint, JWKS fetch call sites that route through these methods).
- `plugins/auth-gitea/backend/atlas_plugin_auth_gitea/provider.py`: `AllauthGiteaTransport.get_profile`, `.get_health`, `.exchange_code`.
- Depends on `plugin-api/python/atlas_plugin_api/` gaining the shared helper proposed in `add-safe-http-helper`.
- No API, schema, or user-facing behavior change — this is a transport-layer hardening fix underneath already-correct OIDC/OAuth protocol validation (state, nonce, PKCE, issuer/audience/signature checks, which are out of scope here).
