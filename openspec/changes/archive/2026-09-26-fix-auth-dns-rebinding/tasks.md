## 1. Prerequisite

- [x] 1.1 Confirm `add-safe-http-helper` has landed and review its final API shape against the composition question in design.md's Open Questions (does it work with an existing `requests.Session`?).

## 2. OIDC provider

- [x] 2.1 Update `RequestsOIDCTransport.get_json` to connect using the address already validated by `_validate_resolved_destination`, via the shared helper, preserving `Host`/SNI for the original hostname.
- [x] 2.2 Apply the same change to `RequestsOIDCTransport.post_form`.
- [x] 2.3 Add a test asserting exactly one DNS resolution occurs per outbound call (mock the resolver and assert call count).
- [x] 2.4 Add a test simulating a changed DNS answer between validation and connection, asserting the request still connects to the originally validated address.

## 3. Gitea provider

- [x] 3.1 Resolve how to pin the connection while keeping `AllauthGiteaTransport._session()`'s allauth-managed session (per design.md Decisions) — via the shared helper if composable, or via a targeted adjustment if not.
- [x] 3.2 Update `AllauthGiteaTransport.get_profile` to connect using the validated address.
- [x] 3.3 Update `AllauthGiteaTransport.get_health` likewise.
- [x] 3.4 Update `AllauthGiteaTransport.exchange_code` likewise.
- [x] 3.5 Add the same resolution-count and changed-DNS-answer tests as for OIDC.

## 4. Verification

- [x] 4.1 Run the existing OIDC and Gitea provider test suites and confirm no regressions.
- [x] 4.2 Manually verify (or test) that TLS certificate validation still succeeds against a real HTTPS endpoint when connecting by pinned IP with the original hostname as SNI.
- [x] 4.3 Confirm the existing address-class policy (link-local/multicast/reserved rejection, loopback dev-gate, private-address allowlist) is unchanged in behavior.
