# Keycloak OIDC authentication example

This disposable development topology is for operators evaluating
standards-based browser OIDC. It runs Atlas, PostgreSQL, and a pinned Keycloak
service, selects only `atlas.auth.oidc`, and demonstrates automatic Principal
and Actor provisioning plus exact provider-owned Group reconciliation.

## Architecture and policy

```text
browser :18080 -> Atlas frontend -> Atlas backend -> PostgreSQL
      |                              |
      +-> localhost:18081       Keycloak <- keycloak.localhost:18081
             public issuer             Docker backchannel discovery
```

Keycloak hostname v2 publishes `localhost:18081` as the issuer and browser
authorization origin, while dynamic backchannel discovery lets Atlas reach the
same service through its Docker-only `keycloak.localhost` alias. Atlas still
requires the discovery document's issuer to equal the public issuer exactly.
The exact Atlas callback is:

```text
http://localhost:18080/auth/browser/v1/providers/atlas.auth.oidc/callback
```

The checked-in [manifest](manifest.yaml) and [lock](lock.yaml) make OIDC the
only selected and default provider. The `atlas-example` realm supplies the
`openid profile email groups` scopes and a `groups` mapper. Atlas automatically
provisions a Principal and linked Actor, updates the allowlisted profile
fields, and maps complete group snapshots exactly:

| Keycloak group      | Atlas Group     | Behavior                                            |
|---------------------|-----------------|-----------------------------------------------------|
| `atlas-platform`    | `oidc-platform` | Provider-owned grant, renewed/removed by exact sync |
| `atlas-readers`     | `oidc-readers`  | Provider-owned grant, renewed/removed by exact sync |
| `unmapped-upstream` | none            | Ignored; it grants no Atlas permission              |

The initializer creates the two Atlas Groups before login. Claims never grant
staff, superuser, Purge Grant, or catalog permissions directly. Ordinary Atlas
owner-Group evaluation remains the authorization boundary.

## Prerequisites

- Docker Engine with Docker Compose v2
- about 4 GB free RAM, 2–4 CPU cores, and 6 GB disk for the first build
- Python 3.11+ to run the browser-like HTTP smoke test

## Start and sign in

From this directory:

```bash
cp .env.example .env
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Open <http://localhost:18080>. Atlas immediately starts the default redirect
flow. Sign in as `oidc-alice` with `ATLAS_OIDC_TEST_PASSWORD` from `.env`.
Keycloak itself is at <http://localhost:18081>; its disposable admin
credentials are also in `.env`.

The realm, users, passwords, database password, Django key, and OIDC client
secret are fixtures. Never reuse any of them. Atlas receives the client secret
only through `ATLAS_OIDC_CLIENT_SECRET`; the manifest and lock contain the
environment-variable reference, not a resolved value.

## Verify provisioning, permissions, and exact removal

Run:

```bash
./smoke.sh
```

The smoke driver performs a real Authorization Code + PKCE browser sequence,
submits the Keycloak login form, follows the Atlas callback, and checks:

1. the public config exposes OIDC only, so no local credential form is offered;
2. the first login creates one stable Principal, External Identity link, and
   Actor, while only `atlas-platform` maps to an Atlas membership;
3. that membership permits creation of a System owned by `oidc-platform`;
4. removing `atlas-platform` through Keycloak's admin API and signing in again
   reuses the same Principal/link and removes only its provider grant;
5. `unmapped-upstream` creates no grant, the now-unowned write is denied, and
   Atlas logout invalidates the local session;
6. the fixture group is restored so the example remains repeatable.

You can also inspect Users, External Identity Links, Actors, and membership
grant provenance in Django admin or with `python manage.py shell`. A manual or
other-provider grant for the same Actor/Group pair would survive this exact
reconciliation; only the authenticating identity link's stale provider grants
are removed.

## Add explicit local break-glass

OIDC-only is intentional. To add password break-glass, edit the manifest and
regenerate the lock/settings; do not expose local endpoints by environment
variable alone. Add `atlas.auth.local` as a second provider while keeping OIDC
the default:

```yaml
auth:
  providers:
    - id: atlas.auth.oidc
      # retain the OIDC policy from this example
    - id: atlas.auth.local
      signup: disabled
      principalProvisioning: preprovisioned
      actorProvisioning: manual
      groupSync: { mode: none }
  default: atlas.auth.oidc
```

Preprovision the local Principal through an operator-controlled command and,
if Django-admin password access is required, separately enable `adminPassword:
{mode: break-glass, principalIds: [...]}` with an exact allowlist. Neither
selection enables anonymous signup: `signup: disabled` remains the server-side
control. Use `/login?choose-provider=1` to reach the explicit provider chooser
instead of the default redirect.

## Logout semantics

The example configures local Atlas logout only. `DELETE
/auth/browser/v1/session` ends the Atlas session first, but it does not promise
to terminate the Keycloak SSO session. A later login may therefore complete
without asking for the password. Production remote logout needs reviewed
provider support, redirect allowlisting, and token-retention policy; an
upstream logout failure must never restore an Atlas session.

## Troubleshooting

- **Discovery cannot connect:** `keycloak.localhost` is intentionally a Docker
  network alias, while the browser uses `localhost`. Do not make the internal
  alias the issuer; keep expected issuer, Keycloak hostname, and source binding
  equal to the public loopback issuer.
- **Initializer or backend waits:** inspect `docker compose logs keycloak
  initializer backend`. Keycloak's management-port readiness check gates Atlas
  startup, and PostgreSQL migrations gate the backend.
- **`invalid_scope` or missing groups:** keep the imported `groups` client
  scope and mapper, and request `groups`. Exact sync rejects incomplete group
  data rather than treating it as an empty authoritative snapshot.
- **Issuer/discovery error:** the discovery document's `issuer` must exactly
  equal `http://localhost:18081/realms/atlas-example`; an internal
  service URL is not an interchangeable issuer alias.
- **Callback rejected:** the realm permits only the exact callback above and
  exact web origin `http://localhost:18080`. If you change `ATLAS_PORT`, update
  `publicOrigin`, realm callback/origin, and regenerated artifacts together.
- **Provisioning fails:** inspect whether the snapshot is complete, the Atlas
  target Groups exist, the source binding matches, and the proposed username
  is not already held by an unrelated Principal/Actor.
- **Login returns to Keycloak immediately:** Atlas logout and IdP logout are
  separate. Use a private window or end the Keycloak session when testing the
  password prompt itself.

## Cleanup

```bash
docker compose down --volumes --remove-orphans
```

This removes the isolated PostgreSQL and Keycloak volumes. All example data is
disposable.

## Production differences

This topology uses Keycloak `start-dev`, plain HTTP, checked-in disposable
fixtures, locally built Atlas images, Docker volumes, Django `runserver`, and
Vite's development server. Production requires HTTPS and secure cookies,
reviewed immutable images, external secret management, durable production
databases/backups, strict proxy and outbound-destination policy, monitored
timeouts/rate limits, tested key rotation and recovery, deliberate IdP/logout
behavior, and a reviewed immutable issuer/source migration plan. Do not import
this realm or copy its secrets into a real deployment.
