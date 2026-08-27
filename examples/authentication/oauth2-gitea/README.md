# Gitea OAuth2 authentication example

This disposable development topology is for operators evaluating Atlas's
provider-specific Gitea login. It runs Atlas, PostgreSQL, and pinned Gitea
`1.27.3`, selects only `atlas.auth.gitea`, and demonstrates automatic
Principal and Actor provisioning with operator-managed memberships.

OAuth 2.0 is an authorization framework, not an identity or group standard.
This example works because Atlas ships a Gitea-specific adapter that knows
Gitea's endpoints and profile schema. Do not reuse this configuration for an
arbitrary OAuth server.

## Architecture and policy

```text
browser :18080 -> Atlas frontend -> Atlas backend -> PostgreSQL
      |                              |
      +-> gitea.localhost:18082 -----+-> Gitea 1.27.3
```

The selected adapter requests exactly `read:user`, uses Authorization Code
with PKCE S256, fetches `GET /api/v1/user`, and keys the External Identity by
Gitea's immutable numeric `User.id` plus the configured instance origin.
Mutable login, name, and email values are profile data, never identity keys.
The exact Atlas callback registered during bootstrap is:

```text
http://localhost:18080/auth/browser/v1/providers/atlas.auth.gitea/callback
```

The installed adapter does not retrieve a complete, paginated teams snapshot,
so `groupSync.mode` is deliberately `none`. The `read:user` scope—and any
other upstream role or scope—grants no Atlas permission. Operators manage
Atlas Group membership independently.

## Prerequisites

- Docker Engine with Docker Compose v2
- about 3 GB free RAM, 2–4 CPU cores, and 5 GB disk for the first build
- Python 3.11+ for the browser-like HTTP smoke test
- loopback subdomains resolving to `127.0.0.1` (modern browsers do this for
  `*.localhost`); otherwise add `127.0.0.1 gitea.localhost` locally

## Start and sign in

From this directory:

```bash
cp .env.example .env
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Open <http://localhost:18080>. Atlas redirects to
<http://gitea.localhost:18082>. Sign in with `ATLAS_GITEA_TEST_USERNAME` and
`ATLAS_GITEA_TEST_PASSWORD` from `.env`, review the requested `read:user`
scope, and authorize Atlas.

The bootstrap is repeatable. It creates or updates disposable users, creates
one OAuth application, and writes Gitea's generated client id and secret to a
Docker volume mounted read-only by Atlas. No generated OAuth secret is
committed, printed by the smoke test, copied into the lock, or exposed to the
frontend. If the Gitea data volume survives but the runtime-secret volume does
not, bootstrap replaces the named disposable OAuth application and issues a
new secret.

## Verify identity, permissions, and logout

Run:

```bash
./smoke.sh
```

The smoke driver performs the actual redirect, Gitea login and consent,
callback, and provisioning journey. It verifies that:

1. only `atlas.auth.gitea` is selected and it uses redirect flow;
2. repeat login reuses one Principal, External Identity link, linked Actor,
   and stable numeric Gitea subject;
3. an authenticated catalog read succeeds as a normal Atlas session;
4. no provider Group grant, staff flag, or superuser flag is derived from the
   OAuth scope, and a write owned by the operator-only `gitea-operators` Group
   is denied;
5. Atlas logout invalidates the local session.

Inspect Principal, Actor, External Identity, and membership state in Django
admin or `python manage.py shell`. To grant ownership, add the Actor to an
Atlas Group through an operator workflow; do not add scopes to the OAuth app
and expect them to become permissions.

## Logout semantics

`DELETE /auth/browser/v1/session` always ends the Atlas session first. The v1
Gitea adapter declares remote logout unsupported, so the Gitea browser session
remains active and another Atlas login may not ask for the password. The UI
and this guide intentionally do not call that an IdP-wide logout.

## Troubleshooting

- **`gitea.localhost` does not open:** verify local `*.localhost` resolution or
  add the loopback hosts entry described above. Keep `instanceOrigin`, Gitea
  `ROOT_URL`, source binding, and allowed destination identical.
- **Bootstrap fails:** inspect `docker compose logs gitea gitea-users
  oauth-bootstrap`. The user bootstrap waits for Gitea health; OAuth bootstrap
  then creates the application before Django imports provider settings.
- **Callback is rejected:** keep the Atlas port at `18080`, or update the
  callback in `gitea/bootstrap_oauth.py`, `auth.publicOrigin`, and generated
  artifacts together, then recreate both example volumes.
- **`invalid_scope`:** Gitea requires a scope. Atlas v1 supports exactly
  `read:user`; `read:organization` is intentionally absent because the adapter
  does not implement complete team pagination.
- **Login works but writes fail:** authentication does not grant ownership.
  Inspect the Actor link and operator-managed Atlas Group memberships.
- **The password prompt is skipped:** Atlas logout did not terminate the
  upstream Gitea session. Use a private window or sign out of Gitea separately.

## Cleanup

```bash
docker compose down --volumes --remove-orphans
```

This removes PostgreSQL, Gitea, repositories, users, OAuth credentials, and
the runtime-secret volume. Everything in the topology is disposable.

## Production differences

This example uses plain HTTP, local builds, SQLite-backed disposable Gitea,
checked-in test passwords, generated secrets in a Docker volume, Django
`runserver`, Vite development serving, and development-only outbound trust.
Production requires HTTPS and secure cookies, reviewed immutable images,
external secret management, durable production databases and backups,
restricted networks/proxies, monitored timeouts and rate limits, deliberate
account recovery, and an audited source-migration plan. Register an exact
production callback and canonical Gitea HTTPS origin. Never copy these users,
passwords, volumes, or development HTTP exceptions into a real deployment.
