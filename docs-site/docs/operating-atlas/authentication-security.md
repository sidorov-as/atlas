---
title: Secure browser authentication
description: Configure origins, outbound identity traffic, credentials, sessions, recovery, rate limits, and observability.
audience: [operator, plugin-author]
page-type: guide
---

# Secure browser authentication

Set `auth.publicOrigin` to the one browser origin users reach. Configure Django
allowed hosts and CSRF trusted origins with exact schemes, hosts, and ports.
Trust forwarded headers only from `auth.trustedProxyAddresses`. Atlas rejects
foreign, scheme-relative, credential-bearing, and ambiguously encoded return
URLs.

Production session cookies are Secure and HttpOnly with SameSite Lax. The CSRF
cookie remains readable by the SPA and is Secure. Login rotates the session id.
Authentication and session responses are non-cacheable.

## Outbound identity traffic

List permitted identity-service origins under
`auth.outboundTrust.allowedDestinations`. Atlas validates discovery, token,
UserInfo, JWKS, redirects, and logout destinations, including resolved
addresses. It rejects cloud metadata targets, unexpected origins, plaintext
downgrades, and credential forwarding to a new origin. Private IdPs require an
explicit destination. Plain HTTP is limited to loopback development fixtures
and requires `allowDevelopmentHttp: true`.

TLS certificate and hostname verification, connection/read/overall deadlines,
and response-size limits stay enabled. Do not add an insecure retry after a TLS
failure.

## Passwords and recovery

Local signup, bootstrap, change, and reset share the generated password
policy. Defaults require at least 15 characters, accept at least 64, and reject
common or user-similar values without truncation. Recovery defaults to
`operator-managed`. Public reset requires explicit verified addresses, mail
delivery, single-use expiry, generic responses, and throttling. A provider
profile email does not silently become a recovery destination.

Django admin password login is separately disabled by default. Break-glass
requires `auth.adminPassword.mode: break-glass` and a non-empty allowlist of
active staff Principal ids. It creates a normal bounded session that can reach
catalog APIs under ordinary authorization. It does not bypass read-only state.

## Sessions, revocation, and retention

Sessions have an absolute, non-sliding lifetime of eight hours by default.
Every authenticated request checks the current Principal, revocation
generation, identity link, source binding, selected provider, and break-glass
allowlist. Shortening the configured lifetime applies from the original
authentication time.

Provider tokens and raw protocol payloads are transient by default. Framework
token persistence, browser storage, request-body tracing, and callback-query
logging must remain disabled or redacted. Remote logout may retain a token only
in bounded protected server-side storage, deleting it on logout or expiry.

Rate limits aggregate credential failures, redirect starts and callback
failures, signup, and recovery across aliases, providers, and workers. Use only
trusted proxy data to determine the client address.

## Safe diagnostics

Use allowlisted failure categories and correlation ids. Never print
credentials, authorization codes, state, access/refresh/ID tokens, client or
bind secrets, raw claims, or upstream bodies. `/healthz/auth/providers/`
reports selected/default state, flow, safe status, callback URL, and category.
It returns 503 if any selected provider is unavailable while still listing
healthy alternatives.

Provider plugins are trusted Python code with server-process privileges. The
SDK context and import rules define collaboration, not containment. Review
package provenance and dependencies before selection.
