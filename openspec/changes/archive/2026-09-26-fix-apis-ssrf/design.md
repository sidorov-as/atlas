## Context

`atlas_plugin_apis.spec_fetch.fetch_spec_content` is the single choke point for resolving a user-supplied `spec_url`: it's called synchronously from `apply_api_spec_source`, which itself is called both from the CRUD API's create/patch handlers (in the HTTP request path — `api-spec-documents` spec's "Setting a spec URL resolves it immediately" scenario depends on this) and from `atlas_plugin_apis.extension_points.due_for_spec_refresh`, invoked periodically by the ingestor. It currently does an unguarded `requests.get(url)`: no IP allowlisting, redirects followed, no size cap, no streaming, and only a coarse "does it parse as YAML/JSON" content check.

A separate, parallel change (`add-safe-http-helper`) is adding a shared SSRF-safe fetch primitive to `plugin-api/python/atlas_plugin_api/`: resolve DNS once, reject private/loopback/link-local/reserved addresses, connect to the verified IP while preserving Host/SNI, re-validate on redirect, stream with a byte cap, HTTPS-only by default. This change is written against that helper's intended shape; if it hasn't landed yet when this change starts implementation, implementation should wait for it rather than duplicate the guard logic here.

## Goals / Non-Goals

**Goals:**
- Close the SSRF hole: no fetch of `spec_url` can reach a private/loopback/link-local/reserved address, follow a redirect into one, or exceed a bounded response size.
- Preserve today's synchronous-resolution contract ("saving an API with a URL source resolves it in the same request") rather than silently turning it into an eventually-consistent background job.
- Keep the YAML/JSON acceptance check meaningfully bounded (size + nesting depth), not just "did `yaml.safe_load` not throw."

**Non-Goals:**
- Moving spec resolution off the synchronous request path entirely. The audit suggested this; this design defers it (see Decisions) rather than bundling an architecture change into a security patch.
- Building a general-purpose allowlist/policy UI for operators — a minimal environment-variable or settings-based allowlist is enough for this change; a richer admin-configurable policy is out of scope.
- Changes to `add-safe-http-helper` itself — that's owned by its own change.

## Decisions

- **Use the shared helper rather than a local guard.** The same "resolve once, verify IP, preserve Host/SNI, bound redirects and size" logic is also needed by `fix-auth-dns-rebinding` (OIDC/Gitea providers). A single shared implementation in `plugin-api/python/atlas_plugin_api/` avoids two independent, potentially-inconsistent SSRF guards. Alternative considered: implement a local one-off guard in `spec_fetch.py` for speed of delivery — rejected because it duplicates security-critical logic that needs to stay correct in two places.

- **Keep the fetch synchronous, but tightly bounded, rather than moving it to a background worker.** The audit's suggested fix included "move fetch off the synchronous request path." This design keeps it synchronous because: (a) the existing spec explicitly promises immediate resolution on save, and changing that is a user-facing behavior change with its own design questions (how does the UI show "pending"? what does patch return before resolution completes? does the ingestor's periodic refresh also need reworking?) that don't belong in a security-fix change; (b) a tight timeout plus a hard byte cap via streaming already bounds the worst case duration and memory use, which was the operational risk the audit was pointing at, not just the SSRF vector itself. Alternative: full async offload — better isolation, but expands this change's blast radius substantially. If synchronous latency turns out to be a problem in practice after this lands, that's its own follow-up change with its own proposal.

- **HTTPS-only by default, operator allowlist for exceptions.** Rejects the audit's "allow HTTP" middle ground by default, since most legitimate spec-hosting is HTTPS; an operator with a genuine internal-HTTP use case opts in explicitly rather than the system trusting HTTP globally.

- **Reject, don't silently downgrade, on redirect into a disallowed address.** A redirect chain that ends at a private IP is treated as a failed resolution (same as today's "fetch failed" path: `spec_resolve_failed = True`, existing `spec_content` untouched) rather than silently stopping at the last-good hop — avoids partial/confusing state.

## Risks / Trade-offs

- **Operators with legitimate internal spec hosts will see a regression** → mitigated by the allowlist; call out clearly in the change's migration notes / release notes.
- **Depending on `add-safe-http-helper` landing first creates a sequencing dependency** → if that change is delayed, this one is blocked from implementation (not from planning). Mitigation: this proposal is written so the helper's expected interface is narrow enough that implementation can start once the helper's shape is stable, even before it's fully merged.
- **Tighter timeouts/size caps could reject some large-but-legitimate OpenAPI specs** (some real-world specs are multi-MB) → mitigate by setting the byte cap generously (e.g. tens of MB) rather than aggressively small, and making it a named constant that's easy to reconsider, not a magic number buried in the fetch call.

## Migration Plan

1. Land `add-safe-http-helper`.
2. Rewrite `fetch_spec_content` to use it, with HTTPS-only default, redirect re-validation, streaming byte cap, and YAML/JSON size+depth limits.
3. Add the allowlist mechanism (config/env-based) for operators who need non-HTTPS or non-public-routable targets.
4. Add tests: loopback (v4/v6), RFC1918, redirect-to-disallowed, DNS rebinding, oversized response, deeply nested YAML.
5. Document the allowlist and the behavior change in release notes, since it can turn a previously-working `specUrl` into a failed resolution for some deployments.
6. No data migration; `spec_resolve_failed` already exists as the failure signal, so failed fetches surface through the existing stale-spec UI indicator.

## Open Questions

- Exact allowlist configuration mechanism (env var list of hosts vs. a settings-based CIDR/host allowlist) — left to implementation; either satisfies this design as long as it's operator-controlled and off by default.
