---
title: Build an authentication provider
description: Implement and test a credential or redirect provider against atlas.auth.providers.v1.
audience: [plugin-author]
page-type: tutorial
---

# Build an authentication provider

Use `atlas.auth.providers.v1` for a browser provider that fits one of two
flows: a single-step credential verifier or a redirect start/callback
protocol. Multi-step provider-owned login UI is outside v1. Core renders the
standard interaction from presentation metadata.

## Two-phase lifecycle

The static `PluginDescriptor.authentication_providers` contribution declares
the provider id, contract version, one flow kind, presentation, config schema,
Django apps, and any required namespaced route module. Composition imports it
before `django.setup()`, so it cannot access models, the database, or the
network.

After Django setup, runtime code creates the provider with resolved typed
namespaced configuration and calls:

```python
register_authentication_provider(provider, owner=PLUGIN.id)
```

Secrets arrive through validated `SecretRef` values and stay backend-only.
Provider code must not read arbitrary environment variables or Core settings.

## Implement the boundary

`CredentialAuthenticationProvider.authenticate()` receives a bounded
`CredentialFlowContext` and ephemeral `CredentialInput`.
`RedirectAuthenticationProvider.begin()` returns a `RedirectChallenge`, and
`complete()` receives the callback context. Core owns attempt state, provider
selection, return URLs, provisioning, sessions, CSRF, logout, and
authorization.

Return `VerifiedIdentity` with:

- the registered provider id;
- an immutable authority `source_id`;
- a non-empty stable subject;
- normalized `ExternalProfile` values;
- provenance-bearing `AssuredAttribute` values; and
- an `ExternalGroupSnapshot` marked `complete`, `unavailable`, or `unsupported`.

A complete snapshot can contain zero groups. Do not return a partial snapshot
as complete. Failures use only `AuthenticationFailure` categories
`invalid_credentials`, `unavailable`, `invalid_result`, or `canceled`.
Exceptions, credentials, tokens, and upstream bodies must not cross the
boundary.

Providers never return a Django User, Actor, Group, permission, staff flag,
session, or authorization decision. They cannot import `server.apps.*`, Core
registries/settings/models/session helpers, or undocumented allauth internals.

## Test and package

Package the provider independently, declare its Plugin API and Core
compatibility, and run the public credential or redirect contract suite with
documented factories. Add provider-specific protocol tests for transport,
timeouts, stable subject, replay, completeness, and any library behavior the
generic kit cannot know. Run the repository import-boundary check as well.

The [custom credential example](https://github.com/sidorov-as/atlas/tree/main/examples/authentication/custom-credentials)
is a minimal separately packaged implementation. Its tests and manifest show
the full selection path. Installed Python plugins are trusted server code;
contract tests verify cooperative conformance and do not sandbox hostile code.

## LDAP search-and-bind mapping

A production LDAP plugin can implement the credential flow without changing
v1:

1. Read private typed server, base-DN, search-filter, bind, TLS, timeout, and pagination configuration.
2. Reject an empty password before any bind. Escape filter and DN values.
3. Search with a bounded service bind and require exactly one result.
4. Verify the submitted password with a non-anonymous user bind. A timeout, transport error, zero/multiple results, or incomplete bind is a failure.
5. Use an operator-declared immutable directory namespace as `source_id` and a stable directory UUID as subject. Do not use a mutable DN, username, or email.
6. Mark profile attributes with their real assurance. Fetch every group page before returning a complete snapshot; otherwise return unavailable.
7. Verify certificates and hostnames, forbid plaintext downgrade, bound response sizes, and map failures to safe categories without exposing account existence.

LDAP protocol security remains the provider's responsibility. Core still owns
eligibility, linking, provisioning, membership grants, session creation, and
authorization. Atlas does not ship or certify a production LDAP plugin or an
OpenLDAP example.
