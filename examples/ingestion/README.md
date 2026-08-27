# Repository ingestion example (Gitea)

This disposable development topology is for operators evaluating Atlas's
universal git ingestion connector. It runs Atlas, PostgreSQL, and pinned
Gitea `1.27.3`, selects `atlas.auth.gitea` (login) and every plugin
`distributions/default/manifest.yaml` selects — `atlas.standard-catalog`,
`atlas.apis`, `atlas.c4`, `atlas.database-schema`, `atlas.ingestion`, and
`atlas.flows`. It provisions three Gitea repositories, each
with a `catalog-info.yaml` manifest derived from the booking-marketplace demo
fixture, registers them against a configured ingestion source, and runs an
ingestion pass automatically at startup so entities are visible immediately
after `docker compose up`.

## Architecture

```text
browser :18090 -> Atlas frontend -> Atlas backend -> PostgreSQL
      |                              |
      +-> gitea.localhost:18092 -----+-> Gitea 1.27.3
```

Ingestion credentials never live in the database. `atlas.ingestion` plugin
config declares one source, `gitea-primary`, pointing at
`http://gitea.localhost:18092` with a bearer-token credential resolved from
the `GITEA_INGESTION_TOKEN` environment variable at process startup. The
three `RegisteredRepository` rows created by this example's bootstrap
reference that source by id and a repository path relative to its `baseUrl`
— never a credential.

Bootstrap runs in stages, each idempotent and safe to rerun:

1. `gitea` starts and `gitea-users` creates a disposable admin account and one
   non-admin "operator" account.
2. `oauth-bootstrap` creates a Gitea OAuth application for Atlas login (the
   same pattern as the
   [Gitea OAuth2 authentication example](../authentication/oauth2-gitea/)) and
   writes the generated client id/secret to a runtime-secrets volume.
3. `repo-bootstrap` creates a Gitea access token for ingestion, the
   `atlas-demo` organization, three repositories
   (`search-discovery`, `payments-payouts`, `booking-reservations`), and
   pushes each repository's curated manifest content via Gitea's contents
   API. `search-discovery` and `payments-payouts` each get a single
   `catalog-info.yaml`; `booking-reservations` gets a `catalog-info.yaml`
   that composes its Resources, APIs, and Components from separate fragment
   files under `.manifests/` via `kind: Include` (see [catalog-info.yaml:
   composing fragments](../../docs-site/docs/concepts/catalog-info-yaml.md#composing-fragments-with-kind-include))
   — the fixture tree lives at
   [`fixtures/booking-reservations/`](fixtures/booking-reservations/). Its
   `booking-db` Resource also declares `spec.databaseSchema`, pointing at
   [`.manifests/db/schema.sql`](fixtures/booking-reservations/.manifests/db/schema.sql)
   (see [catalog-info.yaml: declaring a Database Schema
   source](../../docs-site/docs/concepts/catalog-info-yaml.md#declaring-a-database-schema-source)),
   so ingestion populates its `DatabaseSchema` Facet automatically instead of
   it being entered by hand. The token is written to the same
   runtime-secrets volume.
4. `initializer` runs migrations, pre-creates the owner Groups the fixture
   manifests reference (`search-team`, `booking-team`, `payments-team` —
   `catalog-info.yaml` cannot declare `kind: Group`), registers the three
   `RegisteredRepository` rows against `gitea-primary`, and seeds a Django
   admin superuser via `seed_admin`.
5. `ingest-once` runs `python manage.py ingest` twice. Two passes are needed
   on a cold start: ingestion resolves a repository's `consumesApis`/
   `dependsOn` references within that one repository's pass, and the
   `booking-reservations` fixture references APIs owned by the other two
   repositories. The first pass populates those APIs; the second resolves the
   cross-repository references against them. This is expected, not a bug —
   rerunning `manage.py ingest` is always safe (see
   [Register and ingest a repository](../../docs-site/docs/using-atlas/ingest-repository.md)).
6. `ingestor` starts alongside everything else and stays up: it runs
   `python manage.py runapscheduler`, which registers `atlas.ingestion`'s
   `atlas.ingestion.discovery` and `atlas.ingestion.spec_refresh` jobs in the
   `django_apscheduler`-backed job store and re-runs them every
   `INGESTOR_POLL_INTERVAL` seconds (60 by default; not set in this example's
   `.env`) — so a `catalog-info.yaml` edit is picked up automatically,
   without a manual `manage.py ingest`. It's independent of `ingest-once`
   (which only ever runs its two startup passes and exits) — inspect
   registered jobs under Django admin's **Django apscheduler** section, or
   `docker compose logs ingestor`.

## Prerequisites

- Docker Engine with Docker Compose v2
- About 3 GB free RAM, 2-4 CPU cores, and 5 GB disk for the first build
- Python 3.11+ for the smoke test
- Loopback subdomains resolving to `127.0.0.1` (modern browsers do this for
  `*.localhost`); otherwise add `127.0.0.1 gitea.localhost` locally

## Start the stack

From this directory:

```bash
cp .env.example .env
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

`ingest-once` exits after running its two passes; every other service,
including `ingestor` (see stage 6 above), stays up. Check its log if entities
don't appear:

```bash
docker compose logs ingest-once
```

## Sign in to Gitea

Open <http://gitea.localhost:18092> and sign in with `GITEA_ADMIN_USERNAME`/
`GITEA_ADMIN_PASSWORD` (full administrative access, used by the bootstrap
containers) or `ATLAS_GITEA_OPERATOR_USERNAME`/`ATLAS_GITEA_OPERATOR_PASSWORD`
(a normal account, used for the Atlas OAuth login below) from `.env`. The
`atlas-demo` organization holds the three fixture repositories.

## Sign in to Atlas

**Gitea OAuth** — open <http://localhost:18090>, follow the Gitea login
button, sign in with the operator account above, and authorize Atlas. This
provisions a Principal and linked Actor automatically; it has no owner-Group
membership and cannot write catalog data owned by `search-team`,
`booking-team`, or `payments-team`.

**Django admin** — `initializer` already ran `seed_admin`, which creates an
`admin` superuser (Principal id `1` in a freshly seeded database) and a
`platform-operators` owner Group. This manifest opts into
`auth.adminPassword.mode: break-glass` with `principalIds: [1]` specifically
so that seeded account — and only that account — can authenticate at
<http://localhost:18090/admin/> with the password in `ATLAS_BOOTSTRAP_PASSWORD`
from `.env`. Password login to `/admin/` is otherwise closed by default (see
[Local
authentication](../../docs-site/docs/operating-atlas/local-authentication.md));
logging in through the Gitea OAuth button above does not grant `/admin/`
access — that provisions a separate, non-staff Principal, and is not on the
break-glass allowlist. Use Django admin to inspect **Registered
repositories** and **Conflict records**, and to manage owner-Group
membership (**Group detailss**) for the OAuth principal above.

## Verify the ingested entities

Open the Systems list in the Atlas UI and confirm **Search & Discovery**,
**Booking & Reservations**, and **Payments & Payouts** are present, each
YAML-managed and attributed to its registered repository. Open **Booking &
Reservations** and confirm its `booking-service` Component shows
`consumesApis` resolved to `search-api` and `payments-api`, and an
Architecture Relationship to `payment-service` under **Relations** — this is
the cross-repository reference the two-pass startup ingestion resolves (see
Architecture above).

Open the **Booking DB** Resource and confirm its Schema tab shows `postgresql`
as the dialect with the `guests`, `hosts`, `listings`, `reservations`, and
`reservation_events` tables already populated — from
`fixtures/booking-reservations/.manifests/db/schema.sql`, not entered by
hand — and that the Schema tab is read-only (see [Database Schema:
repository-managed
schemas](../../docs-site/docs/features/database-schema.md#repository-managed-schemas)).
Open its ER Diagram tab to see the parsed relations between those tables.

## Edit a manifest and re-ingest

1. In the Gitea web UI, open `atlas-demo/payments-payouts` and edit
   `catalog-info.yaml` — for example, change the `payments-payouts` System's
   `description`.
2. Commit the change on the `main` branch.
3. Wait for `ingestor`'s next poll (`INGESTOR_POLL_INTERVAL`, 60 seconds by
   default) and skip to step 4 — or, to see the change immediately instead of
   waiting, run a manual ingestion pass. `GITEA_CLIENT_ID`/`GITEA_CLIENT_SECRET`/
   `GITEA_INGESTION_TOKEN` only exist in the `backend` container's *entrypoint*
   shell (sourced from the runtime-secrets volume at container start) — a
   plain `docker compose exec backend python manage.py ingest` runs in a
   fresh shell without them and fails with `ImproperlyConfigured: Gitea
   requires GITEA_INSTANCE_ORIGIN and GITEA_CLIENT_ID`. Source the same files
   first:

   ```bash
   docker compose exec backend sh -c '
     . /run/atlas-ingestion/gitea.env
     . /run/atlas-ingestion/ingestion.env
     export GITEA_CLIENT_ID GITEA_CLIENT_SECRET GITEA_INGESTION_TOKEN
     python manage.py ingest
   '
   ```

   This applies to any `manage.py` command you run via `exec` in this
   example — `shell`, `dumpdata`, etc. — not just `ingest`.

4. Reload the **Payments & Payouts** System detail page and confirm the
   description changed. There is no Django-admin action or UI button to
   trigger a run on demand — `ingestor`'s recurring poll and the manual
   command above are the only triggers (`ingest-once` only runs at startup).

## Verify the round trip automatically

```bash
./smoke.sh
```

The smoke driver brings up (if needed) or reuses the running stack, confirms
the three fixture entities exist, confirms `booking-db`'s `DatabaseSchema`
Facet was populated from `db/schema.sql` (dialect `postgresql`, parsed
`ok`, and the five expected tables), edits `atlas-demo/search-discovery`'s
manifest via the Gitea contents API, reruns ingestion, and asserts the edited
field is reflected in the reconciled entity.

## Troubleshooting

- **`gitea.localhost` does not open:** verify local `*.localhost` resolution
  or add the loopback hosts entry described above.
- **`ingest-once` logs `no connector registered for source_id`:** the
  `gitea-primary` source isn't resolving from `atlas.ingestion` plugin
  config; confirm `generated/selected_plugins.py`'s `PLUGIN_CONFIGS` still
  declares it and that `GITEA_INGESTION_TOKEN` is exported before `manage.py`
  runs (check the runtime-secrets volume was populated by `repo-bootstrap`).
- **`booking-service`'s `consumesApis` didn't resolve:** confirm
  `ingest-once` actually ran its pass twice (`docker compose logs
  ingest-once`); a single manual `manage.py ingest` run right after startup
  is expected to still show one unresolved cross-repository reference until a
  second pass runs. See [Troubleshoot repository
  ingestion](../../docs-site/docs/using-atlas/troubleshoot-ingestion.md) for
  the general failure-mode reference.
- **`ImproperlyConfigured: Gitea requires GITEA_INSTANCE_ORIGIN and
  GITEA_CLIENT_ID` from a `docker compose exec backend python manage.py ...`
  command:** expected — see [Edit a manifest and
  re-ingest](#edit-a-manifest-and-re-ingest) above for the `exec` incantation
  that sources the runtime-secrets volume first.
- **Repository bootstrap fails:** inspect `docker compose logs gitea
  gitea-users repo-bootstrap oauth-bootstrap`. Both bootstrap containers are
  idempotent and safe to rerun (`docker compose up repo-bootstrap
  oauth-bootstrap`).
- **`/admin/` rejects the bootstrap password:** confirm `ATLAS_BOOTSTRAP_PASSWORD`
  in `.env` matches what you're typing, and that `initializer` completed
  successfully (`docker compose logs initializer`). Password login only
  works for the seeded `admin` account (Principal id `1`) — the manifest's
  `adminPassword.principalIds` break-glass allowlist — never for the Gitea
  OAuth principal.

## Cleanup

```bash
docker compose down --volumes --remove-orphans
```

This removes PostgreSQL, Gitea, repositories, users, tokens, and the
runtime-secret volume. Everything in this topology is disposable.

## Production differences

This example uses plain HTTP, local builds, SQLite-backed disposable Gitea,
checked-in test passwords, generated secrets in a Docker volume, Django
`runserver`, Vite development serving, and development-only outbound trust
(`allowDevelopmentHttp: true` on the ingestion source and the Gitea auth
provider). Production requires HTTPS, an external secret manager for the
ingestion credential (and any `ssh-key` source's private key via `fromFile`),
restricted networks, and reviewed images; `ingestor` itself (`manage.py
runapscheduler`) is already the same long-running process a production
deployment would run, though there this example's one-shot `ingest-once`
container (only useful to populate a disposable demo immediately at
`docker compose up`) would not exist. Never copy these users, passwords,
volumes, or development HTTP exceptions into a real deployment.
