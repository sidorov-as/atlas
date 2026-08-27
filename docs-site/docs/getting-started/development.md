---
title: Run Atlas locally
description: Start the development topology, load the booking demo, and inspect a catalog entity and its relationships.
audience:
  - evaluator
  - catalog-user
  - operator
page-type: tutorial
---

# Run Atlas locally

This tutorial starts a fresh supported checkout with the Atlas development
stack and the booking demo. You will apply database migrations, load the demo,
sign in, and inspect a seeded System's relationships.

## Starting state and prerequisites

Start from the repository root with:

- Docker Desktop or another Docker installation with Compose v2;
- the repository checked out locally;
- ports `5173`, `8000`, and `5432` available; and
- a database you may replace with demo data.

The development topology mounts the backend and frontend source directories
into their containers and reloads them while you work. It is for local
development. For a deployment-like setup, see the
[production-like topology](../deployment/production.md).

## Result

After completing the tutorial, <http://localhost:5173> shows the seeded
booking-platform catalog. Sign in as the local administrator, open **Booking &
Reservations**, and view its catalog relationships.

## Account and permissions

The demo seed creates the local account `admin` with password
`atlas-demo-admin-password`. The account is a Django superuser and global Atlas
administrator. These credentials are disposable local-development data; never
reuse them for a shared or production-like deployment.

## 1. Create the local environment file

From the repository root, copy the checked-in development defaults:

```shell
cp core/backend/.env.example core/backend/.env
```

The development Compose file overrides the database host to the `postgres`
service. The copied file deliberately contains development-only defaults such
as `DJANGO_SECRET_KEY=change-me` and local origins. Review the [environment
variable reference](../configuration/environment-variables.md) before changing
them. If the copy fails or Compose later says that the environment file is
missing, follow [Compose cannot read the development environment
file](../deployment/troubleshooting.md#compose-cannot-read-the-development-environment-file).

## 2. Start the development topology

Start the source-mounted stack and leave it running in this terminal:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml up --build
```

Compose starts PostgreSQL first, waits for it to become healthy, runs the
one-shot `migrate` service to apply Core and selected-plugin migrations, then
starts the backend, frontend, and ingestion scheduler once `migrate` completes
successfully. Wait until the backend reports healthy and the frontend reports
its local URL before continuing. If the command cannot connect to Docker,
cannot bind a port, or stops during an image build, use [The development stack
does not build or
start](../deployment/troubleshooting.md#the-development-stack-does-not-build-or-start).
If a migration is rejected by the repository's safety checks, follow
[Migration was rejected as
unsafe](../deployment/troubleshooting.md#migration-was-rejected-as-unsafe)
instead of bypassing the check. For a database connection error, missing-table
error, or another Django migration failure, use [Database migrations do not
complete](../deployment/troubleshooting.md#database-migrations-do-not-complete).

In a second terminal at the repository root, inspect the service state:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml ps
```

The `postgres`, `backend`, `frontend`, and `ingestor` services should be
running, with PostgreSQL and the backend reporting healthy; `migrate` should
show as exited with status `0` — it is a one-shot migration step, not a
long-running service. If a service exits with a non-zero status or never
becomes ready, use [Confirming a topology is actually
up](../deployment/troubleshooting.md#confirming-a-topology-is-actually-up).

## 3. Load the booking demo

!!! warning "This replaces the local database contents"
    `seed_booking_demo --yes` flushes the entire database used by this topology
    before it creates the demo. Do not run it against data you need to keep.

Run the checked-in demo seed:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml exec backend python manage.py seed_booking_demo --yes
```

The command recreates the local administrator and populates Systems,
Components, Resources, APIs, database schemas, flows, and relationships. Wait
for the final `Seeded ...` summary. If the command exits before then, follow
[The booking demo does not
load](../deployment/troubleshooting.md#the-booking-demo-does-not-load). A
partial run may not be usable.

## 4. Verify backend health

Check the backend independently of the browser:

```shell
curl --fail http://localhost:8000/healthz/
```

The command must exit successfully with an HTTP 200 response. A failure means
the backend is not serving yet; follow [The backend health check
fails](../deployment/troubleshooting.md#the-backend-health-check-fails) before
diagnosing the frontend.

## 5. Sign in and inspect the catalog

1. Open <http://localhost:5173>. Atlas redirects an unauthenticated browser to
   the sign-in page.
2. Enter username `admin` and password `atlas-demo-admin-password`, then select
   **Log in**.
3. On the Atlas home page, select **Systems**.
4. Select the **Booking & Reservations** row once. A preview panel opens with
   its owner, descriptive metadata, and a control labelled **Open full
   details**.
5. Open the full details and confirm the **Overview** tab describes the booking
   lifecycle.
6. Select **Relations**. Confirm that **Catalog Relations** lists related
   catalog entities. The separate **Architecture Relationships** section is
   where explicitly declared runtime interactions are shown.

If the login form rejects the seeded account, use [The seeded administrator
cannot sign in](../deployment/troubleshooting.md#the-seeded-administrator-cannot-sign-in).
If **Booking & Reservations** is absent or an entity page shows an error, use
[The seeded catalog is missing or does not
render](../deployment/troubleshooting.md#the-seeded-catalog-is-missing-or-does-not-render).

This confirms the browser session, catalog API, seeded data, entity detail
route, and relationship endpoints are working. See [entity
references](../concepts/entity-references.md) for the identity rules behind the
displayed relations.

## Verification checklist

- `docker compose ... ps` shows `postgres`, `backend`, `frontend`, and
  `ingestor` running, and `migrate` exited with status `0`.
- `curl --fail http://localhost:8000/healthz/` exits successfully.
- `admin` can sign in at <http://localhost:5173>.
- **Booking & Reservations** opens from the Systems list.
- Its **Relations** tab renders **Catalog Relations** and **Architecture
  Relationships** without an error alert.

## Next steps by role

The [visual tour of the demo catalog](catalog-tour.md) covers the home, list,
preview, detail, relations, and System Context states used in this tutorial.

- **Catalog users:** continue to [Using Atlas](../using-atlas/index.md) for
  catalog navigation and entity workflows.
- **Operators:** continue to [Operating Atlas](../operating-atlas/index.md) for
  supported topologies, configuration, and routine operations.
- **Plugin authors:** continue to [Plugin Development](../plugin-development/index.md)
  to choose an extension mechanism and learn how distributions compose plugins.
- **Evaluators:** return to [Overview](../overview/index.md) or explore [Features
  and Integrations](../features/index.md).
