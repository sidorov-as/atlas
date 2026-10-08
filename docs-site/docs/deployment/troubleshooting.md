# Troubleshooting

Start with the exact symptom you can observe. Run commands from the repository
root and keep the same Compose file and environment file as the topology you
are diagnosing. The commands below use the development topology for problems
specific to Getting Started.

## Production-like initializer, gateway, and plugin failures

When the production-like topology does not serve Atlas, inspect services in
dependency order: `postgres`, `initializer`, `backend`, `ingestor`, then
`frontend`. The initializer applies migrations and collects static files; do
not start dependent services manually after it fails.

```shell
docker compose --env-file core/backend/.env ps
docker compose --env-file core/backend/.env logs postgres initializer backend ingestor frontend
```

For a plugin state reported by `/healthz/plugins/` as degraded, inspect that
plugin's configuration and logs. Restarting only clears an in-process degraded
marker. It does not correct missing configuration or a composition contract.

## An authentication provider is missing

Read `/auth/browser/v1/config` and `/healthz/auth/providers/`. An installed
package remains hidden and unusable until its id appears in the authoritative
`auth.providers` list and its runtime registers with the declared flow. Check
the manifest, selected owning plugin, lock, and generated settings. Regenerate
instead of editing runtime modules. If a redirect provider is default, open
`/login?choose-provider=1` to inspect the other selected choices.

## Signup or local login is rejected

Signup is closed by default. Enable it only through the local provider's
`signup` policy; exposing an allauth URL or local form does not override the
server check. Local login also requires `atlas.auth.local` to be selected.
Django admin password login has a separate disabled-by-default break-glass
policy and exact active-staff allowlist.

For an existing local account, distinguish an invalid credential from a
selection or CSRF failure by its safe category and correlation id. Do not log
the submitted username/password object or weaken generic invalid-credential
responses.

## OIDC redirect, discovery, or issuer fails

Confirm `atlas.auth.oidc` and its plugin are selected. Compare the discovery
URL with the metadata location and compare metadata `issuer` byte for byte
with `expectedIssuer`. Internal service names are not issuer aliases. Verify
the exact callback under `auth.publicOrigin`, client registration, allowed
algorithms, scopes, outbound destination policy, and trusted certificate.

A callback/state, nonce, PKCE, signature, audience, token-time, or UserInfo
subject failure must stop before provisioning. Do not retry without the
failed check or print the code, state, tokens, raw claims, or upstream body.
See [OIDC authentication](../operating-atlas/oidc-authentication.md).

## Authentication reports CSRF or origin failure

Match `auth.publicOrigin`, the browser's complete scheme/host/port,
`DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS`. Trust forwarded
headers only from configured proxy addresses. CORS does not replace CSRF.
Rejecting a foreign return URL is expected behavior.

## A provider is unavailable but fallback should work

Inspect `/healthz/auth/providers/`. The endpoint reports every selected
provider independently and may return 503 while another provider is healthy.
Open the permanent provider chooser. If fallback is absent, confirm it is
selected; installation alone is insufficient. Keep timeouts and TLS verification in
place; do not turn a runtime outage into an insecure retry.

## Login has an identity collision or provisioning failure

Use the correlation id and inspect exact provider, source, and subject through
`manage_auth_identity inspect`. Do not join accounts by matching username or
email. A link owned by another Principal requires an operator-reviewed exact
operation. For `preprovisioned`, the link must exist before login. For
`restricted`, recheck verified attribute provenance and current eligibility.

If login succeeds but ownership access is absent, inspect the Principal-to-Actor
link. Manual Actor mode permits a session without an Actor; automatic mode can
fail on a naming collision instead of claiming an unrelated Actor.

## Group membership is missing, stale, or unexpectedly retained

Check the provider's snapshot status, explicit mapping, target Group, Actor
link, grant source, expiry, link/source state, and current mode. Exact mode
requires a complete snapshot and removes only that identity's omitted grants.
Additive mode retains prior grants. A manual or other-provider grant keeps the
effective membership after one source disappears. Classify legacy grants
before enabling exact sync. See [Group membership reconciliation](../operating-atlas/group-reconciliation.md).

## Login works but a write is denied

Authentication does not grant authorization. Check the Actor link, effective
owner-Group membership, resource owner, Purge Grant when relevant, and the
selected PolicyEvaluator. Then check `AccountAccess.read_only`: it independently
denies writes even for a superuser or effective owner. Do not remap provider
groups or use break-glass to bypass a read-only restriction.

## Logout appears incomplete

Atlas invalidates its local session first. The upstream browser session remains
unless the provider declares and completes remote logout, so a later redirect
may authenticate without another password prompt. Confirm that Atlas protected
routes reject the old local session; test upstream logout separately.

## Distribution composition fails

Run the resolver and validator against the manifest and lock before building.
Correct the named manifest entry or plugin contract, then resolve a new lock;
do not hand-edit generated modules or the lock; integrity comes from `uv.lock` and
`package-lock.json`. See [Fix distribution
composition errors](../operating-atlas/composition-errors.md).

## Diagram or feature rendering fails

Confirm backend health and the selected plugin state. Then preserve the
failing browser request and inspect the corresponding backend and frontend
logs. A missing feature tab usually means its plugin is not selected or is
disabled; a plugin error needs its own configuration or runtime cause fixed.
Do not reseed or reset a database to conceal a rendering failure. For C4
rendering dependencies and user-facing controls, follow the [C4 feature guide](../features/c4.md);
for an unavailable entity, restore a compatible kind provider before retrying.

## Compose cannot read the development environment file

If Compose reports that `core/backend/.env` does not exist, check that the
example and destination paths are relative to the repository root:

```shell
test -f core/backend/.env.example
test -f core/backend/.env
```

If the example exists and the destination does not, create it:

```shell
cp core/backend/.env.example core/backend/.env
```

Do not replace an existing customized file just to clear this symptom. If the
file exists but Compose rejects a value, compare its variable names with
`.env.example` and the [environment variable
reference](../configuration/environment-variables.md). Keep secrets out of
terminal output and issue reports.

## The development stack does not build or start

- If the command cannot connect to the Docker daemon, start Docker and confirm
  that `docker version` reports both a client and server before retrying.
- If Docker reports that an address is already in use, free ports `5173`,
  `8000`, and `5432`, or set the Compose `FRONTEND_PORT`, `BACKEND_PORT`, or
  `POSTGRES_HOST_PORT` override in `core/backend/.env` before starting again.
- If an image build fails, read the first failing build step. Fix the reported
  dependency, network, or source error, then rerun the same `up --build`
  command; a later service health error is a separate symptom covered below.
- If the backend reports a permission error writing to the mounted source tree
  (on a Linux host whose user is not UID/GID `1000`), rebuild the backend image
  with matching IDs: `docker compose --env-file core/backend/.env -f
  docker-compose.dev.yml build --build-arg APP_UID=$(id -u) --build-arg
  APP_GID=$(id -g)`. The backend and ingestor images run as a non-root
  `appuser` (UID/GID `1000` by default), not as root; see [Containers run as
  a non-root user](production.md#containers-run-as-a-non-root-user).

After correcting the cause, retry the documented command:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml up --build
```

## Confirming a topology is actually up

```shell
docker compose --env-file core/backend/.env ps
curl --fail http://localhost:8080/healthz/
```

(Use `http://localhost:8000/healthz/` and add `-f docker-compose.dev.yml` for the development
topology.) A failing `curl` means the gateway or backend is not serving yet. Check `ps` for a
service that is not `healthy`/`running`, then follow its logs.

For Getting Started, use the development Compose file consistently:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml ps
docker compose --env-file core/backend/.env -f docker-compose.dev.yml logs postgres migrate backend frontend ingestor
```

Start with the first service that is exited (with a non-zero status) or
unhealthy. PostgreSQL must be healthy before the one-shot `migrate` service
can run, `migrate` must complete successfully before the backend and ingestor
start, and the backend must be healthy before the frontend starts. Correct
that earliest failure, rerun `up --build`, and repeat `ps` before continuing.

!!! note "First start on either topology"
    On the production-like topology, the `initializer` service must finish migrations and
    `collectstatic` before the backend, ingestor, and gateway will start serving; on the
    development topology, the `migrate` service plays the same gating role (without
    `collectstatic`). If nothing responds yet, check that service's logs first — the other
    services are waiting on it and may not be failing independently.

## The frontend can't reach the backend

In the development topology, the Vite dev server proxies `/api`, `/_allauth`, and `/admin` to the
backend. If those requests fail, confirm the backend container is healthy (see above)
before investigating the frontend configuration.

## Database migrations do not complete

On a fresh or reset development database, the one-shot `migrate` service runs
before `backend` and `ingestor` start; if it fails, neither of them starts.
Confirm this is the failure by checking service state and the `migrate`
service's own logs:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml ps
docker compose --env-file core/backend/.env -f docker-compose.dev.yml logs migrate
```

A connection-refused or name-resolution error means `migrate` could not reach
PostgreSQL; diagnose the `postgres` service and its logs first. If Django
names a specific migration, keep that error, correct the underlying cause, and
rerun `up --build` — Compose recreates and reruns the exited `migrate`
service.

If the topology is already running and you pulled new migrations, inspect the
plan without changing the database, then apply them directly against
`backend`:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml exec backend python manage.py showmigrations
docker compose --env-file core/backend/.env -f docker-compose.dev.yml exec backend python manage.py migrate
```

Do not fake migration records or edit the database by hand. If Atlas
explicitly classifies the migration as unsafe, use the next procedure
instead.

## Migration was rejected as unsafe

A migration touching a dropped column/table, or narrowing a field's nullability without a
default, fails the safety check by design. The check protects a rolling upgrade
breaking a still-running previous release. If the change genuinely is safe (e.g. reviewed
maintenance-mode work), mark the specific operation with a required justification comment rather
than working around the check.

## The booking demo does not load

The demo command is successful only after it prints its final `Seeded ...`
summary. A missing-table error normally means migrations were not applied to
this development database; complete [Database migrations do not
complete](#database-migrations-do-not-complete), then run the seed again.

For any other failure, preserve the command output and inspect the backend log:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml logs backend
```

The command flushes the target database before loading the demo. Retry it only
when that database is disposable, using the exact development-topology command
from Getting Started, and wait for the final summary before signing in.

## The backend health check fails

If `curl --fail http://localhost:8000/healthz/` reports connection refused,
confirm that the backend container is running and that `BACKEND_PORT` has not
changed the host port. If it returns an HTTP error, inspect the backend logs:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml ps backend
docker compose --env-file core/backend/.env -f docker-compose.dev.yml logs backend
```

Return to [Confirming a topology is actually
up](#confirming-a-topology-is-actually-up) if the backend is unhealthy. Do not
continue to browser diagnosis until the health request succeeds.

## The seeded administrator cannot sign in

The `admin` / `admin` account exists only after `seed_booking_demo --yes`
finishes with its `Seeded ...` summary. If the account is rejected:

1. Confirm that the seed command completed against the same development
   topology and database now serving the browser.
2. Confirm that backend health succeeds.
3. Open the frontend at the configured development origin (by default
   <http://localhost:5173>). Do not call the backend login endpoint on a
   different origin.
4. Inspect the browser request and backend log. A refused `/api` or
   `/_allauth` request is a frontend-to-backend symptom; an origin or CSRF
   rejection means the configured allowed/trusted origins do not match the URL
   in the browser.

Use [The frontend can't reach the backend](#the-frontend-cant-reach-the-backend)
for proxy failures. Do not expose passwords, cookies, CSRF tokens, or secret
settings in copied logs.

## The seeded catalog is missing or does not render

If **Booking & Reservations** is absent, first confirm that the seed printed
its final summary and that the Systems list is not filtered. A blank list after
a successful seed usually means the browser and seed command are using
different running projects or databases.

If the entity exists but its detail, Relations, or diagram view shows an error,
check backend health and then inspect the backend and frontend logs:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml logs backend frontend
```

Record the failing browser request and the first corresponding server error.
Do not rerun the destructive seed merely to hide a rendering or API failure.

## Starting over locally

```shell
docker compose --env-file core/backend/.env down --volumes
```

Removes that topology's database and generated static data, not repository files. See
[Operations](operations.md) for the development-topology equivalent.
