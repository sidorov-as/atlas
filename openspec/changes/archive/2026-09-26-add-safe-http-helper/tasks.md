## 1. Module scaffolding

- [x] 1.1 Add `plugin-api/python/atlas_plugin_api/safe_http.py`.
- [x] 1.2 Define the public API surface: a request function/class taking at minimum a URL, optional max redirect hops, optional max response bytes, optional HTTP opt-in flag, and returning a response object (or streamed body) plus final resolved address for logging/debugging.
- [x] 1.3 Export the new public symbols from `atlas_plugin_api/__init__.py`, matching the package's existing explicit-import convention.

## 2. DNS resolution and address verification

- [x] 2.1 Implement hostname resolution returning all candidate addresses (both A and AAAA where applicable).
- [x] 2.2 Implement the private/loopback/link-local/multicast/unique-local/reserved range check against `ipaddress.ip_address(...).is_private / is_loopback / is_link_local / is_multicast / is_reserved`, plus any IPv4-mapped-IPv6 edge cases (e.g. `::ffff:127.0.0.1`).
- [x] 2.3 Reject the request if every resolved address fails verification; if only some do, decide and document whether to use a verified address or reject outright (prefer reject-if-any-ambiguity for safety).

## 3. Pinned connection

- [x] 3.1 Implement connecting to a specific verified IP while sending the original hostname as `Host` and TLS SNI — spike the `requests`/`urllib3` integration approach first (custom `HTTPAdapter`/transport override) per design.md's flagged TLS-validation risk, before committing to the final shape.
- [x] 3.2 Confirm TLS certificate validation still checks against the original hostname, not the pinned IP.

## 4. Redirect handling

- [x] 4.1 Implement per-hop redirect interception (disable the underlying client's automatic redirect following; handle redirects in the helper's own loop).
- [x] 4.2 Re-run DNS resolution and verification on each redirect target before following it.
- [x] 4.3 Enforce the caller-supplied max-hops limit, including a `0` value meaning "never follow."

## 5. Bounded streaming reads

- [x] 5.1 Implement streamed body reads with a hard byte cap, aborting mid-read once exceeded, independent of `Content-Length`.

## 6. URL/scheme constraints

- [x] 6.1 Reject URLs with embedded credentials or a fragment.
- [x] 6.2 Default-reject non-HTTPS URLs; support an explicit per-call opt-in for HTTP.

## 7. Tests

- [x] 7.1 Unit tests: RFC1918, loopback (v4 and v6), link-local (including a `169.254.169.254` case), multicast, IPv6 unique-local — each rejected before any connection attempt.
- [x] 7.2 Unit tests: redirect to a disallowed address is not followed; redirect to a verified address is followed; zero-hop configuration follows nothing.
- [x] 7.3 Unit test: oversized response aborts mid-stream even when `Content-Length` under-reports or is absent.
- [x] 7.4 Unit tests: credentials-in-URL rejected, fragment rejected, HTTP rejected by default and allowed when opted in.
- [x] 7.5 A simulated DNS-rebinding test: mock the resolver to return a public address on first resolution and a private address on a second resolution, and confirm the helper's pinned-connection approach is immune (never re-resolves after the initial verification).

## 8. Documentation

- [x] 8.1 Docstring the module and public API with the intended consumers (`fix-apis-ssrf`, `fix-auth-dns-rebinding`) and the specific threat model it defends against, so future contributors understand why this exists instead of a plain `requests.get`.
