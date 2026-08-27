# Local authentication example

This is the smallest runnable Atlas authentication topology. It selects only
`atlas.auth.local`, keeps anonymous signup closed, and bootstraps one disposable
administrator through an idempotent operator command. Use it to understand the
Atlas Principal/Actor/Group boundary before configuring an external provider.

## Architecture and policy

```text
browser :18080 -> Vite development server -> Atlas backend -> PostgreSQL
                                             |
                                             +-- atlas.auth.local only
```

The checked-in [manifest](manifest.yaml) is authoritative. Its lock and
generated backend settings are committed beside it so the topology does not
inherit authentication selection from the repository's default distribution.
The selected/default provider is `atlas.auth.local`; signup is `disabled`,
Principal provisioning is `preprovisioned`, Actor provisioning is `manual`,
and external group synchronization is `none`.

The initializer runs migrations and `seed_admin` once PostgreSQL is healthy.
That command reads the password from `ATLAS_BOOTSTRAP_PASSWORD`, never from a
command-line argument, and idempotently creates or updates:

- a Django User, which is the authenticating **Principal** and is marked staff
  and superuser for this disposable example;
- an Atlas **Actor** linked to that Principal, which is its catalog identity;
- the `local-platform` **Group**, plus a manual membership linking the Actor to
  that owner Group.

Those are separate records. Authentication alone does not create ownership or
turn a Principal into an Actor, and Group membership is not the same thing as
Django superuser status.

## Prerequisites

- Docker Engine with Docker Compose v2
- roughly 2 GB of free RAM, 2 CPU cores, and 4 GB of disk during the first
  image build
- `curl` and POSIX `sh` only if you run the smoke test

## Start

From this directory:

```bash
cp .env.example .env
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Open <http://localhost:18080> and sign in with `ATLAS_BOOTSTRAP_USERNAME` and
`ATLAS_BOOTSTRAP_PASSWORD` from your local `.env`. The values supplied in
`.env.example` are deliberately disposable and must never be reused.

To rerun bootstrap without putting the password in shell history:

```bash
read -rs ATLAS_BOOTSTRAP_PASSWORD
printf '\n'
export ATLAS_BOOTSTRAP_PASSWORD
docker compose exec -T backend python manage.py seed_admin \
  --username local-admin \
  --email local-admin@example.test \
  --group local-platform
unset ATLAS_BOOTSTRAP_PASSWORD
```

Local password validation uses the same policy as bootstrap, signup, password
change, and reset: at least 15 characters by default, no silent truncation,
and common-password/user-similarity checks. Public recovery remains disabled;
use the operator-controlled bootstrap procedure to rotate this example account.

## Verify identity and permissions

After login:

1. Open `/admin/` and inspect the bootstrap User/Principal.
2. Inspect the linked Actor and `local-platform` Group. The Actor membership is
   the catalog ownership input; the superuser flag is an independent Django
   administrative property.
3. Create a System owned by `group:local-platform`. The bootstrap account is
   allowed because this fixture is both a superuser and a member of that owner
   Group.
4. Run `./smoke.sh`. It verifies closed signup, creates a disposable ordinary
   Principal with a linked Actor but no owner-Group membership, logs in through
   the public gateway, reads an authenticated API, confirms a write owned by
   `local-platform` is denied, logs out, and confirms the session ended.

The smoke user is intentionally not added to `local-platform`. Its denied
write demonstrates that a valid session is not an authorization grant.

## Logout

Use the application logout action or send `DELETE /auth/browser/v1/session`
with the current CSRF token. Local logout invalidates the Atlas session; there
is no upstream identity-provider session in this topology.

## Troubleshooting

- **Compose asks for a variable:** copy `.env.example` to `.env`; Compose never
  requires an untracked file merely to render when `--env-file .env.example`
  is supplied.
- **Initializer exits:** inspect `docker compose logs initializer postgres`.
  Weak bootstrap passwords are rejected by the shared password validators.
- **Login says invalid credentials:** check the username in `.env`, then rerun
  the bootstrap command above with a newly entered strong password.
- **Signup returns 403:** this is expected. Hiding signup in the UI is not the
  control; the backend policy rejects the operation.
- **Authenticated but unable to edit:** inspect Principal activity/read-only
  state, Actor linkage, owner-Group membership, and ordinary permissions as
  separate layers. Do not enable signup or superuser as a workaround.
- **Port 18080 is busy:** change `ATLAS_PORT` and
  `DJANGO_CSRF_TRUSTED_ORIGINS` together, then update `publicOrigin` in
  `manifest.yaml` and regenerate the lock/settings before treating the variant
  as authoritative.

## Cleanup

```bash
docker compose down --volumes --remove-orphans
```

The named PostgreSQL volume is removed by `--volumes`. Anything created inside
the example is disposable.

## Production differences

This topology uses Django `runserver`, Vite's development server, plain HTTP,
development-only HTTP trust, locally built images, and example credentials.
A production deployment needs reviewed immutable images, HTTPS and secure
cookies, a real public origin/proxy policy, secret-manager references, backups,
monitoring, a non-development process manager, deliberate administrator
recovery, and tested restore/rotation procedures. Keep signup closed unless an
operator explicitly accepts and configures self-registration.
