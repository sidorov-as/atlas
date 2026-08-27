---
title: Authentication routes and diagnostics
description: Exact browser gateway routes, safe failure categories, provider diagnostics, and compatibility boundaries.
audience: [operator, plugin-author]
page-type: reference
---

# Authentication routes and diagnostics

The canonical browser gateway prefix is `/auth/browser/v1/`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `config` | Selected safe presentation metadata and default behavior |
| `GET` | `session` | Current Core session state |
| `DELETE` | `session` | Local-first logout |
| `POST` | `providers/{provider_id}/credentials` | Invoke a selected credential provider |
| `POST` | `providers/{provider_id}/start` | Begin a selected redirect provider |
| `GET` | `providers/{provider_id}/callback` | Complete a selected redirect provider |
| `POST` | `signup` | Local signup, only when explicitly enabled |

`/login?choose-provider=1` opens the permanent chooser without automatically
starting the default redirect. Existing `/_allauth/browser/v1/*` and selected
`/accounts/*` paths are compatibility surfaces. They enforce the same
selection, signup, CSRF, rate-limit, and session policy and are not the public
contract for new clients.

## Safe failures

Provider contract failures are `invalid_credentials`, `unavailable`,
`invalid_result`, or `canceled`. Gateway errors may also report a sanitized
category from this fixed set:

| Category | Typical status | Meaning |
| --- | --- | --- |
| `provider_not_available` | 404 | Provider is unknown, disabled, or unselected |
| `wrong_flow` | 404 | Route does not match the provider's declared flow |
| `invalid_request` | 400 | Request shape or size is invalid |
| `invalid_credentials` | 400 | Credential verification failed without account disclosure |
| `unsafe_return_url` | 400 | Redirect target failed the origin policy |
| `invalid_state` | 400 | Callback state is missing, expired, replayed, or browser/provider/source mismatched |
| `invalid_result` | 400 or 502 | Provider returned a declared invalid result or violated its contract |
| `canceled` | 400 | The upstream interaction was canceled |
| `provisioning_failed` | 403 | Linking, eligibility, Actor, profile, or reconciliation failed closed |
| `authentication_state_changed` | 409 | Policy/source generation changed during the attempt; retry from the start |
| `rate_limited` | 429 | A shared authentication budget is exhausted |
| `provider_unavailable` | 503 | Runtime registration, upstream service, or provider execution is unavailable |

A response contains `category`, `stage`, `correlationId`, and `retryable`, with
no exception text, credentials, token, raw claims, or upstream body. HTTP 429
also includes `Retry-After`; switching provider or compatibility route does
not reset the aggregate budget.

## Provider diagnostics

`GET /healthz/auth/providers/` evaluates selected providers independently and
returns:

- provider id, selected/default flags, and flow kind;
- `available` or `unavailable` plus an allowlisted category;
- the canonical callback URL; and
- a correlation id.

The endpoint returns 503 when any selected provider is unavailable but still
lists healthy alternatives. It never authenticates a user or returns provider
configuration, subjects, claims, secrets, tokens, or raw exception text.

`GET /healthz/plugins/` has a different purpose: it reports selected plugin
lifecycle and sticky runtime failures. Use authentication diagnostics for
provider registration, callback, and bounded upstream health.
