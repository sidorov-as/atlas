---
title: OIDC authentication
description: Enable and verify Atlas's optional OpenID Connect provider without exposing credentials.
audience:
  - operator
page-type: how-to
---

# Enable OIDC authentication

## Prerequisites

- A working Atlas installation using the supported Compose topology.
- An OIDC issuer and a client registered with that issuer.
- Private runtime storage for the client secret.
- A selected `atlas.auth.oidc` plugin and provider entry in the authoritative
  distribution manifest.

## Outcome

Atlas includes the first-party `atlas.auth.oidc` plugin when the distribution selects it. The plugin verifies OIDC and returns a normalized identity and completeness-aware group snapshot; Authentication Core owns linking, provisioning, reconciliation, and the browser session. Group names are not permissions: Atlas still evaluates its centralized policy for every request.

An existing Principal's account-wide read-only flag survives repeated OIDC
login and reconciliation. For read-only access from the first request, prepare
the Principal and exact link under `preprovisioned` policy as described in
[Principal and Actor provisioning](identity-provisioning.md#prepare-a-preprovisioned-identity).

## Configure the provider

1. Configure the plugin's typed namespaced block. Keep the client secret as an
   environment reference:

   ```yaml
   plugins:
     - id: atlas.auth.oidc
       config:
         discoveryUrl: https://issuer.example.test/.well-known/openid-configuration
         expectedIssuer: https://issuer.example.test
         clientId: atlas
         clientSecret: {fromEnv: ATLAS_OIDC_CLIENT_SECRET}
         scopes: [openid, profile, email, groups]
         groupsClaim: groups
   ```

   The discovery URL is fetched metadata; the expected issuer is the exact, immutable identity-source identifier. Atlas rejects a mismatch instead of trusting the fetched document. `OIDC_CLIENT_SECRET` is resolved in memory through a secret reference; never place it in a distribution lock, generated artifact, frontend setting, terminal transcript, or support ticket.

   Existing `OIDC_ISSUER` deployments must move to `discoveryUrl` and add
   `expectedIssuer`; follow the [migration runbook](authentication-migration.md).
2. Select `atlas.auth.oidc` under `auth.providers`. Choose Principal and Actor
   provisioning, profile ownership, and group reconciliation explicitly. OIDC
   groups affect only the mappings in this Core policy.
3. Register the exact public callback:
   `/auth/browser/v1/providers/atlas.auth.oidc/callback`. The complete URI is
   `auth.publicOrigin` plus that path.
4. Request `openid` and the profile/group scopes used by the configured
   claims. Atlas verifies Authorization Code with PKCE S256, state, nonce,
   signature and allowed algorithm, exact issuer, audience/authorized party,
   token times, and UserInfo subject equality.
5. Configure exact browser origins and allowed outbound identity-service
   destinations. Resolve and validate a new lock, then deploy it.

## Verify

Open Atlas at the configured public origin and select OIDC. Confirm that the
callback establishes a session and repeated login reuses the same
provider/source/subject link. Verify the expected Principal, Actor, profile
fields, and mapped grant sources. Test one permitted and one denied catalog
action. For exact sync, remove a mapped upstream group and confirm the next
complete login removes only that identity's grant.

## Fallback, diagnostics, and logout

For a local recovery choice, select `atlas.auth.local` as a second provider,
keep `signup: disabled`, and leave OIDC as the default. Operators reach local
credentials through `/login?choose-provider=1`; a failed redirect also offers
that chooser without immediately starting OIDC again. Installing local auth or
enabling Django admin password login does not add it to the chooser.

Check `/healthz/auth/providers/` for selected/default state, flow kind, safe
availability category, correlation id, and the canonical callback. A provider
outage does not disable a healthy selected fallback. Atlas logout always ends
the local session first. It ends the upstream OIDC session only when remote
logout is configured and completes successfully.

## Troubleshooting

| Symptom | Safe action |
| --- | --- |
| No OIDC option is offered | Confirm the plugin is selected, then confirm discovery URL, expected issuer, client id, and secret are all available at startup. |
| Redirect or callback is rejected | Compare the public host, CSRF trusted origin, and issuer client registration exactly; include scheme and non-default port. |
| Provider rejects the client | Check the client id and secret in private runtime configuration. Do not print the secret. |
| Login succeeds but expected access is absent | Confirm the configured claim name and its returned group names, then assign Atlas permissions through the normal policy administration path. |
| Browser reports CSRF/CORS failure | Use the real browser origin in the matching Django allow-list; CORS is not a substitute for CSRF trust. |
| Discovery works but issuer is rejected | Compare the metadata `issuer` and configured `expectedIssuer` byte for byte. Do not substitute an internal service URL. |
| Exact reconciliation rejects login | Confirm the groups claim is complete, mapped target Groups exist, and every page was retrieved. Missing data is not an empty snapshot. |
| Logout returns to the IdP without a password prompt | Atlas always ends its own session. Upstream logout occurs only when the selected provider declares and completes remote logout. |

See [Group membership reconciliation](group-reconciliation.md), [Secure
browser authentication](authentication-security.md), the [Keycloak example](https://github.com/sidorov-as/atlas/tree/main/examples/authentication/oidc-keycloak),
and [symptom-oriented troubleshooting](../deployment/troubleshooting.md).
