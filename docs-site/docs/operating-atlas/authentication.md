---
title: Choose an authentication method
description: Compare Atlas browser authentication providers and select the right operator guide and runnable example.
audience: [operator]
page-type: guide
---

# Choose an authentication method

Atlas authentication providers verify a browser user and establish the same
Core-managed Django session. They do not make catalog APIs accept an upstream
OIDC or OAuth access token. Atlas does not currently ship API bearer-token,
machine-to-machine, or SAML authentication.

## Decision matrix

| Need | Choose | Provider id | Group behavior | Guide and example |
| --- | --- | --- | --- | --- |
| Operator-created username/password accounts | Local credentials | `atlas.auth.local` | Manual | [Local authentication](local-authentication.md), [example](https://github.com/sidorov-as/atlas/tree/main/examples/authentication/local) |
| Corporate SSO from Keycloak, Okta, Entra ID, Auth0, or another conforming OpenID Provider | OIDC | `atlas.auth.oidc` | `none`, `additive`, or `exact` from an explicit mapping | [OIDC](oidc-authentication.md), [Keycloak example](https://github.com/sidorov-as/atlas/tree/main/examples/authentication/oidc-keycloak) |
| Login through Gitea | Gitea-specific OAuth2 | `atlas.auth.gitea` | Manual in v1 | [Gitea](gitea-authentication.md), [example](https://github.com/sidorov-as/atlas/tree/main/examples/authentication/oauth2-gitea) |
| A single-step directory or proprietary credential verifier | Custom credential plugin | Plugin-defined | Provider capability plus Core policy | [Provider SDK](../plugin-development/authentication-provider-sdk.md), [fixture example](https://github.com/sidorov-as/atlas/tree/main/examples/authentication/custom-credentials) |
| GitHub, GitLab, or another OAuth2 service | A provider-specific adapter, if Atlas actually ships one | Adapter-defined | Adapter-defined | Atlas currently ships only the Gitea OAuth2 adapter |
| SAML, passkeys, multi-step custom UI, or API tokens | Unsupported by provider contract v1 | none | none | Design and ship a separate compatible capability before selecting it |

OAuth 2.0 defines delegated authorization, not a stable identity, profile, or
group schema. An endpoint URL and a JSON path are not enough to make a safe
generic identity provider. Use only a provider-specific adapter that defines a
stable subject and its protocol checks.

## What selection controls

The distribution manifest is authoritative. It contains an ordered, non-empty
`auth.providers` list and an `auth.default` that names one selected provider.
Installing a provider package does not select it. Direct calls to an installed
but unselected provider are rejected.

The default controls the first `/login` interaction. Other selected providers
remain available at `/login?choose-provider=1`. A redirect provider can be the
default while local credentials remain an explicit recovery choice. Selecting
local credentials does not open signup; `signup: disabled` is the default and
server-side control.

Use the [manifest reference](../reference/distribution-manifest.md#authentication)
for every field. Resolve and validate a new lock after changing selection.

## Identity and authorization remain separate

A provider returns a stable `(provider, source, subject)` identity plus
assured profile data and, when supported, a group snapshot. Authentication
Core resolves the Principal, provisions or links its Actor, reconciles mapped
Group grants, and creates the session. The PolicyEvaluator then authorizes
ordinary Atlas state.

Provider roles, groups, claims, and OAuth scopes cannot set staff or superuser
status, create Purge Grants, change `read_only`, or bypass the PolicyEvaluator.
Read [Principal and Actor provisioning](identity-provisioning.md) and [Group
membership reconciliation](group-reconciliation.md) before enabling automatic
provisioning.

## Operational limits

Atlas detects upstream removal at the next successful verification. Existing
sessions have a finite absolute lifetime, eight hours by default, and exact
provider grants have their own finite freshness. Atlas v1 does not provide
SCIM or back-channel deprovisioning. For urgent removal, block or deactivate
the Principal or revoke its exact link. A local password reset/change also
advances the Principal's revoke-all generation. See the [migration and
revocation runbook](authentication-migration.md).

Review [authentication security](authentication-security.md) before exposing a
provider outside a development topology. The runnable examples are disposable
learning environments, not production templates.
