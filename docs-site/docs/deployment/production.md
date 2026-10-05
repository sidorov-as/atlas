---
title: Production-like topology
description: Prepare, start, and verify Atlas with immutable Compose images and a same-origin gateway.
audience:
  - operator
page-type: how-to
---

# Run the production-like topology

Use this topology for the supported immutable-image deployment shape: no
source mounts, no frontend development server, and one public gateway origin.
It is the supported Compose workflow closest to a production installation. It
does not cover Kubernetes, horizontal scaling, or a particular external ingress
provider.

## Prerequisites

- Docker Desktop or Docker Engine with Compose v2.
- A checkout containing the distribution you intend to build.
- A private `core/backend/.env` file created from
  `core/backend/.env.example`.
- An available host port (default `8080`).

## Outcome

The `frontend` gateway serves Atlas at one origin. PostgreSQL remains on the
internal database network; the initializer applies migrations and collects
static files before the backend, ingestor, and gateway accept traffic.

## Supported topology

| Service | Exposure | Responsibility |
| --- | --- | --- |
| `frontend` | `${ATLAS_PORT:-8080}` on the host | Serves the compiled SPA and Django static files; proxies application routes to the backend. |
| `backend` | Internal application network | Serves Django and the HTTP API after its health check succeeds. |
| `ingestor` | Internal database network | Runs the platform scheduler (`manage.py runapscheduler`) and the jobs that selected plugins contribute, such as ingestion. |
| `initializer` | Internal database network, one-shot | Runs `migrate --noinput` and `collectstatic --noinput`. |
| `postgres` | Internal database network | Stores Atlas data and reports readiness before initialization begins. |

The development topology mounts source code and exposes the Vite and backend
ports for local iteration. See the [deployment overview](index.md) for that
workflow.

## Production-like preflight

Complete this checklist before starting the services.

- [ ] **Secrets:** replace `DJANGO_SECRET_KEY=change-me` and the example
      `POSTGRES_PASSWORD` with unique, non-example values. Keep
      `core/backend/.env` out of version control. The production settings refuse
      to start with a missing, example, or shorter-than-50-character
      `DJANGO_SECRET_KEY`, and Compose refuses to start without an explicit
      `POSTGRES_PASSWORD`. If OIDC is enabled, set `OIDC_DISCOVERY_URL`,
      `OIDC_EXPECTED_ISSUER`, and `OIDC_CLIENT_ID` and protect
      `OIDC_CLIENT_SECRET` in the same way; leave all OIDC values unset for
      local authentication only.
- [ ] **Host and origin:** set `DJANGO_ALLOWED_HOSTS` to every hostname that
      will reach Django. Set `DJANGO_CSRF_TRUSTED_ORIGINS` to the complete
      browser origins, including scheme and non-default port, such as
      `https://atlas.example.test`. The public gateway is same-origin, so
      `DJANGO_CORS_ALLOWED_ORIGINS` is normally only needed for a deliberately
      separate browser client.
- [ ] **TLS boundary:** Compose exposes HTTP on `ATLAS_PORT`; it does not
      configure a TLS-terminating ingress. `DJANGO_SECURE_SSL_REDIRECT`
      defaults to `true`, so an external TLS proxy must supply
      `X-Forwarded-Proto: https` before you start the services. Align the
      public hostname and HTTPS origin with the host and CSRF values above
      first; only set `DJANGO_SECURE_SSL_REDIRECT=false` if you are
      deliberately running without TLS (e.g. a local production-like trial).
- [ ] **Database state:** choose the database name, user, and password before
      the first start. The supplied topology creates and owns a named local
      Compose volume; do not treat `down --volumes` as a recovery procedure
      for data you need to retain. Backup and restore procedures are covered
      separately in this section.
- [ ] **Composition:** build the intended checked-in distribution and review
      its selected plugins and configuration before deployment. Follow
      [Assembling a distribution](../configuration/distributions.md) for
      manifest and composition validation; this page does not change plugin
      selection at runtime.
- [ ] **Startup order:** leave Compose to start the services. `postgres` must
      become healthy; `initializer` must then finish successfully; `backend`
      must become healthy before `frontend` starts. Do not expose the gateway
      as ready if that chain has failed.
- [ ] **Health endpoint:** decide the URL your monitor will call. With the
      default local port it is `http://localhost:8080/healthz/`; external
      monitoring must use the actual public origin.

See [Environment variables](../configuration/environment-variables.md) for
field ownership and defaults.

## Containers run as a non-root user

The backend, initializer, and ingestor images run as an unprivileged `appuser`
(UID/GID `1000`), not as root. The production stage owns its application and
static directories, so no host volume needs adjusting. If you mount a host
directory that the process must write to, make it writable by that UID/GID, or
rebuild with `--build-arg APP_UID=<uid> --build-arg APP_GID=<gid>` to match your
host.

## Start Atlas

```shell
docker compose --env-file core/backend/.env up --build
```

The first image build can take time. Keep the command output visible until the
initializer finishes and the backend health check passes.

## Verify the result

In a second terminal, check the services and the gateway health endpoint:

```shell
docker compose --env-file core/backend/.env ps
curl --fail http://localhost:8080/healthz/
```

Replace `8080` with your configured `ATLAS_PORT`; for an externally served
installation, use its actual public URL. A successful health response confirms
that the standard application checks passed. To inspect the selected plugins, use
`/healthz/plugins/`; it returns each plugin's `active`, `disabled`, or
`degraded` state and returns HTTP 503 if any selected plugin is degraded.

Open the same gateway URL in a browser and confirm that a direct refresh of a
client-side route still loads. This checks the SPA fallback and same-origin
routing path.

## If preflight or startup fails

| Symptom | Safe next action |
| --- | --- |
| `initializer` exits unsuccessfully | Inspect `docker compose --env-file core/backend/.env logs initializer`; do not start dependent services manually. |
| Gateway is up but Django rejects requests | Compare the request hostname with `DJANGO_ALLOWED_HOSTS` and its complete browser origin with `DJANGO_CSRF_TRUSTED_ORIGINS`. |
| Browser redirects to HTTPS unexpectedly or loops | Set `DJANGO_SECURE_SSL_REDIRECT=false` for local HTTP, or correct the TLS proxy and forwarded protocol before enabling it. |
| Health endpoint fails | Inspect `backend`, `initializer`, and `postgres` logs in startup order. |
| A plugin health check is degraded | Inspect the affected plugin's logs and distribution configuration; restarting only clears the in-process degraded marker, not its underlying cause. |

For logs, shutdown, and migrations, see [Operations](operations.md). For
symptom-oriented diagnosis, see [Troubleshooting](troubleshooting.md).
