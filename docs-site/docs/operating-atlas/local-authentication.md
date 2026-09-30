---
title: Local authentication and administrator access
description: Sign in with Atlas's built-in username-and-password login, understand its browser session, and follow the supported recovery process.
audience:
  - operator
page-type: guide
plugin-id: atlas.auth.local
---

# Local authentication and administrator access

Use this guide for installations that use Atlas's built-in local account
provider (`atlas.auth.local`). The manifest must select it; having Core
installed does not make local login callable. Local accounts use username and
password credentials. See [Choose an authentication method](authentication.md)
for mixed-provider and fallback deployments.

## Prerequisites

- A running Atlas topology with a browser origin allowed by Django.
- `atlas.auth.local` present in `auth.providers` and, when desired, selected as
  `auth.default`.
- An existing local account whose credentials were provisioned through the
  installation's controlled process.
- For Django administration, an existing Django staff or superuser account.

## What you can do

You can sign in through the Atlas UI, check that the browser session works,
and use Django administration when you have the required access. The guide
also explains when an installation owner must handle account recovery.

## Sign in with a local account

1. Open the Atlas browser URL. Unauthenticated catalog routes redirect to
   `Log in`.
2. Enter the account's username and password, then select `Log in`.
3. Confirm that the catalog home page opens. Navigate to a catalog page and
   refresh it; the page should remain available while the session is valid.
4. When finished, use the application's logout control, then confirm that a
   protected catalog route returns to `Log in`.

For a disposable development database only, the
[booking demo](../getting-started/development.md#account-and-permissions)
creates `admin` / `admin`. That command first flushes the selected database,
so do not use these credentials to bootstrap an installation or in shared or
production-like environments.

## Session and browser-origin behavior

Atlas uses the same Core-managed Django session for local and external login.
The session cookie is HTTP-only.
When the frontend starts, it restores the current session and sends Django's
CSRF value with state-changing requests.

- do not copy session cookies or CSRF values into tickets, logs, or shell
  history;
- access Atlas through the configured browser origin; and
- if sign-in or a later write is rejected for CSRF, match the complete origin
  (scheme, host, and non-default port) in
  `DJANGO_CSRF_TRUSTED_ORIGINS`. Use
  [the configuration reference](../configuration/environment-variables.md#change-the-public-host-or-port)
  for the related host and CORS settings.

Logging out ends the browser session through Atlas. The absolute lifetime is
`auth.sessionMaxAgeSeconds`, eight hours by default, and activity does not
extend it. Every request rechecks current active/blocked state and revocation
generation. See [Secure browser authentication](authentication-security.md).

## Administrator access

The Django administration site is at `/admin/` on the backend origin. Existing
valid staff sessions may use it. Password login to admin is a separate policy
and defaults to disabled, even when local catalog login is selected. Enabling
`auth.adminPassword.mode: break-glass` requires an exact allowlist of active
staff Principal ids. A successful break-glass login creates a normal bounded
session that can also call catalog APIs under ordinary authorization. Use the
site from an operator-controlled network and never reuse demo credentials.

Atlas distinguishes the login Principal from the catalog Actor. A successful
local login does not create or link an Actor and does not grant
ownership-based catalog permissions on its own. Read
[Auth and identity](../concepts/auth-and-identity.md) and
[Permissions](../concepts/permissions.md) before changing account or group
relationships in administration.

## Supported recovery boundary

Self-service signup is closed by default through the server-side account
policy. Hiding the UI is not the control. Public password recovery also remains
closed while `auth.recovery.mode` is `operator-managed`. Bootstrap the first local
administrator without putting its password in an argument or repository file:

```shell
export ATLAS_BOOTSTRAP_PASSWORD='use-a-generated-secret-of-15-or-more-characters'
uv run python manage.py seed_admin --username admin --email admin@example.com
unset ATLAS_BOOTSTRAP_PASSWORD
```

The command is idempotent, applies the shared password validators, and also
ensures the administrator has a linked Actor and owner Group. Alternatively,
pipe a secret to `--password-stdin`. The default policy requires at least 15
characters and rejects common or user-similar values. Do not use database edits, the demo seed,
or a Compose-volume reset as credential recovery:

- `seed_booking_demo --yes` deliberately destroys the selected database before
  adding the disposable demo administrator;
- `docker compose ... down --volumes` removes the topology's local data and
  does not recover an account; and
- no Atlas UI action can promote an unknown account to administrator.

If an installation loses access to all administrator accounts, use the
deployment owner's approved identity and data-recovery process. Record the
affected topology and preserve the database before taking destructive action.
[Operations](../deployment/operations.md) documents the supported commands and
boundaries for local data resets. This guide does not cover broader backup and
restore procedures.

## Troubleshooting

| Symptom | Safe check |
| --- | --- |
| The demo administrator is rejected | Verify that `seed_booking_demo --yes` completed against the same disposable development database, then follow [The seeded administrator cannot sign in](../deployment/troubleshooting.md#the-seeded-administrator-cannot-sign-in). |
| Login or a write fails with an origin or CSRF error | Compare the browser's complete origin with `DJANGO_CSRF_TRUSTED_ORIGINS`; do not expose cookies, CSRF values, passwords, or secret settings in logs. |
| A valid login has insufficient catalog access | Check the Principal-to-Actor link and the Actor's group membership using the concepts above; authentication and authorization are separate. |
| The local form is absent or valid credentials are rejected | Confirm `atlas.auth.local` is selected. Open `/login?choose-provider=1` when a redirect provider is the default. |
| Admin password login is rejected | Confirm break-glass is explicitly enabled and that the exact active staff Principal id is allowlisted. Local provider selection alone is insufficient. |
| No administrator can sign in | Follow the controlled recovery boundary above. Do not run demo seeding or remove volumes against data that must be retained. |

## Next steps

- Review [OIDC authentication](oidc-authentication.md) before enabling
  standards-based single sign-on.
- Run the isolated [local authentication example](https://github.com/sidorov-as/atlas/tree/main/examples/authentication/local)
  for disposable end-to-end verification.
- Return to [Operating Atlas](index.md) for topology and routine operations.
- Use [Troubleshooting](../deployment/troubleshooting.md) for observable
  backend, gateway, database, and authentication symptoms.
