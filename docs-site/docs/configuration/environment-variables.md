---
title: Environment configuration reference
description: Configure Atlas for each topology and find the owner and behavior of every supported environment field.
audience:
  - operator
page-type: reference
---

# Configure Atlas

Atlas reads operator-provided values from `core/backend/.env`. Copy the
checked-in template, keep the resulting file private, and pass it to Compose:

```shell
cp core/backend/.env.example core/backend/.env
docker compose --env-file core/backend/.env …
```

This reference covers fields read by Atlas settings and the Compose variables
that choose exposed ports. Plugin configuration and distribution selection are
build-time concerns; see [Assembling a distribution](distributions.md).
Catalog title, tagline, logo, and icon are not environment variables. See
[Catalog branding](catalog-branding.md).

## Operator tasks

### Configure a local development topology

Use the template values and start the source-mounted topology:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml up --build
```

The development Compose file sets `DJANGO_ENV=development` and connects backend
services to `postgres:5432`. It exposes the frontend, backend, and optionally
PostgreSQL on host ports. Change `FRONTEND_PORT`, `BACKEND_PORT`, or
`POSTGRES_HOST_PORT` when a default port conflicts with a local service.
See [Development topology](../deployment/development.md).

### Prepare a production-like topology

Before building immutable images, replace the example signing key and database
password, set `DJANGO_DEBUG=false`, and configure the public host and full
browser origin. Use an `https://` origin only when an external TLS proxy
terminates TLS. The production Compose file sets `DJANGO_ENV=production`, runs
the backend against `postgres:5432`, and exposes the gateway port
(`ATLAS_PORT`).

Follow the complete [production-like preflight](../deployment/production.md)
before starting this topology.

### Change the public host or port

Change `ATLAS_PORT` to move the local gateway listener. Set
`DJANGO_ALLOWED_HOSTS` to each hostname Django should serve and
`DJANGO_CSRF_TRUSTED_ORIGINS` to each full browser origin (scheme, host, and
non-default port). A port mapping does not update either Django allow-list.
Use `DJANGO_CORS_ALLOWED_ORIGINS` for a separate browser client. The supported
production-like gateway is same-origin.

### Allow an internal spec_url host

An `atlas.apis` API entity with `spec_source: url` resolves `spec_url` only
over HTTPS, and only to a publicly-routable address, by default — a fetch
that would otherwise reach a private, loopback, link-local, or other
reserved address is rejected and surfaces the same way as any other failed
resolution (the API keeps its last-known-good spec content and is flagged as
stale). If a deployment intentionally hosts specs on an internal Git or
artifact server reachable only over HTTP, or only at a private address, add
its hostname to `ATLAS_APIS_SPEC_URL_ALLOWLIST` (comma-separated for more
than one host). This is a deliberately narrow, deny-by-default exception:
only the listed hostnames are exempted, and only from the HTTPS and
address-reservation checks — every other fetch-safety behavior (redirect
re-validation, response size limit) still applies.

### Enable optional OIDC

The distribution manifest and the OIDC plugin's namespaced `config` are the
authoritative configuration. Select `atlas.auth.oidc`, set `discoveryUrl` and
`expectedIssuer` separately, and keep `clientSecret` as a `{fromEnv: ...}`
reference. The `OIDC_*` settings below are a temporary compatibility projection
for existing deployments, not a way to select the provider. Follow [OIDC
authentication](../operating-atlas/oidc-authentication.md) for the current
manifest and plugin shape.

## Field reference

`Required` applies to the stated configuration; it does not mean that a value
merely appears in the example file. `Compose` means Compose consumes the value,
while Django does not. Values marked **secret** belong in a private environment
file or an equivalent secret store injected at runtime.

| Field                           | Owner and type                                                                                     | Default / required state                                                                                                                          | Secret handling                                                                                                                                 | Topology                                                | Related guide                                                                      |
|---------------------------------|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------|------------------------------------------------------------------------------------|
| `DJANGO_ENV`                    | Compose environment selector; string                                                               | Template: `development`; Compose overrides it to `development` or `production`                                                                    | Not secret                                                                                                                                      | Both Compose topologies                                 | [Supported topologies](../deployment/index.md)                                     |
| `DJANGO_SECRET_KEY`             | Django signing key; string                                                                         | Template: `change-me`; production (`DJANGO_ENV=production`) requires a unique value at least 50 characters long and refuses to start otherwise    | **Secret**; never commit the real value                                                                                                         | Both                                                    | [Production-like preflight](../deployment/production.md#production-like-preflight) |
| `DJANGO_DEBUG`                  | Django debug flag; boolean                                                                         | Template: `true`; set `false` for production-like use                                                                                             | Not secret                                                                                                                                      | Both                                                    | [Production-like topology](../deployment/production.md)                            |
| `DJANGO_LOG_TRACEBACKS`         | Include exception tracebacks in JSON logs; boolean                                                 | `false`                                                                                                                                           | Not secret, but tracebacks can contain exception messages that key-based redaction does not remove; enable only where the data is not sensitive | Both                                                    | [Production-like topology](../deployment/production.md)                            |
| `DJANGO_ALLOWED_HOSTS`          | Django host allow-list; comma-separated strings                                                    | Template: `localhost,127.0.0.1,0.0.0.0`; required for each deployed hostname                                                                      | Not secret                                                                                                                                      | Both                                                    | [Change the public host or port](#change-the-public-host-or-port)                  |
| `DJANGO_CSRF_TRUSTED_ORIGINS`   | Django CSRF origin allow-list; comma-separated absolute origins                                    | Template: `http://localhost:5173,http://localhost:8080`; required for each browser origin that submits requests                                   | Not secret                                                                                                                                      | Both                                                    | [Change the public host or port](#change-the-public-host-or-port)                  |
| `DJANGO_CORS_ALLOWED_ORIGINS`   | Django CORS allow-list; comma-separated absolute origins                                           | Template and settings default: `http://localhost:5173`; set only for separate browser clients                                                     | Not secret                                                                                                                                      | Both                                                    | [Change the public host or port](#change-the-public-host-or-port)                  |
| `DJANGO_SECURE_SSL_REDIRECT`    | Django HTTPS redirect flag; boolean                                                                | Template default: `false` for local HTTP; production Compose default: `true` — set `false` only when deliberately running without TLS termination | Not secret                                                                                                                                      | Production-like                                         | [Production-like preflight](../deployment/production.md#production-like-preflight) |
| `POSTGRES_DB`                   | PostgreSQL database name; string                                                                   | `atlas`                                                                                                                                           | Not secret                                                                                                                                      | Both Compose topologies                                 | [Production-like preflight](../deployment/production.md#production-like-preflight) |
| `POSTGRES_USER`                 | PostgreSQL database user; string                                                                   | `atlas`                                                                                                                                           | Treat according to local database policy; it is not a password                                                                                  | Both Compose topologies                                 | [Production-like preflight](../deployment/production.md#production-like-preflight) |
| `POSTGRES_PASSWORD`             | PostgreSQL password and Django database credential; string                                         | Template: `atlas`; production Compose has no default and refuses to start until it is explicitly set                                              | **Secret**; never commit the real value                                                                                                         | Both Compose topologies and direct backend              | [Production-like preflight](../deployment/production.md#production-like-preflight) |
| `DJANGO_DATABASE_HOST`          | Django database hostname; string                                                                   | Template: `localhost`                                                                                                                             | Not secret                                                                                                                                      | Direct backend only; Compose overrides it to `postgres` | [Deployment overview](../deployment/index.md)                                      |
| `DJANGO_DATABASE_PORT`          | Django database port; integer                                                                      | Template: `5432`                                                                                                                                  | Not secret                                                                                                                                      | Direct backend only; Compose overrides it to `5432`     | [Deployment overview](../deployment/index.md)                                      |
| `CONN_MAX_AGE`                  | Django database connection lifetime; integer seconds                                               | Settings default: `60`; optional                                                                                                                  | Not secret                                                                                                                                      | Both and direct backend                                 | [Production-like topology](../deployment/production.md)                            |
| `POSTGRES_HOST_PORT`            | Compose PostgreSQL host-port mapping; integer                                                      | `5432`; optional                                                                                                                                  | Not secret                                                                                                                                      | Development Compose only                                | [Development topology](../deployment/development.md)                               |
| `FRONTEND_PORT`                 | Compose Vite host-port mapping; integer                                                            | `5173`; optional                                                                                                                                  | Not secret                                                                                                                                      | Development Compose only                                | [Development topology](../deployment/development.md)                               |
| `BACKEND_PORT`                  | Compose backend host-port mapping; integer                                                         | `8000`; optional                                                                                                                                  | Not secret                                                                                                                                      | Development Compose only                                | [Development topology](../deployment/development.md)                               |
| `ATLAS_PORT`                    | Compose gateway host-port mapping; integer                                                         | `8080`; optional                                                                                                                                  | Not secret                                                                                                                                      | Production-like Compose only                            | [Change the public host or port](#change-the-public-host-or-port)                  |
| `DJANGO_STATIC_ROOT`            | Django collected-static directory; filesystem path                                                 | Settings default: Core `staticfiles` directory; Compose overrides it to `/var/www/django/static`                                                  | Not secret                                                                                                                                      | Direct backend only; Compose supplies its own value     | [Production-like topology](../deployment/production.md)                            |
| `INGESTOR_POLL_INTERVAL`        | Ingestion worker poll period; integer seconds                                                      | `60`; optional                                                                                                                                    | Not secret                                                                                                                                      | Both                                                    | [Ingestion feature guide](../features/ingestion.md)                                |
| `ATLAS_APIS_SPEC_URL_ALLOWLIST` | `atlas.apis` `spec_url` fetch-safety allowlist; comma-separated hostnames                          | Unset (empty; every `spec_url` must be HTTPS and resolve to a publicly-routable address); optional                                                | Not secret                                                                                                                                      | Both                                                    | [Allow an internal spec_url host](#allow-an-internal-spec_url-host)                |
| `OIDC_DISCOVERY_URL`            | `atlas.auth.oidc` OpenID Provider Configuration document URL; string                               | Unset disables the compatibility environment projection; required when it is used                                                                 | Not secret                                                                                                                                      | Both                                                    | [Enable optional OIDC](#enable-optional-oidc)                                      |
| `OIDC_EXPECTED_ISSUER`          | Exact issuer identifier that discovery metadata and ID tokens must contain; string                 | Required with `OIDC_DISCOVERY_URL`; never inferred from discovery                                                                                 | Not secret                                                                                                                                      | Both                                                    | [Enable optional OIDC](#enable-optional-oidc)                                      |
| `OIDC_ISSUER`                   | Deprecated alias for `OIDC_DISCOVERY_URL`; despite its old name, it was treated as a discovery URL | Accepted temporarily only when `OIDC_EXPECTED_ISSUER` is also set; emits a deprecation warning                                                    | Not secret                                                                                                                                      | Both                                                    | [Enable optional OIDC](#enable-optional-oidc)                                      |
| `OIDC_CLIENT_ID`                | `atlas.auth.oidc` client identifier; string                                                        | Unset; required when OIDC is enabled                                                                                                              | Not secret                                                                                                                                      | Both                                                    | [Enable optional OIDC](#enable-optional-oidc)                                      |
| `OIDC_CLIENT_SECRET`            | `atlas.auth.oidc` client secret; string resolved through `SecretRef`                               | Unset; required by the OIDC configuration when enabled                                                                                            | **Secret**; resolved in memory and never written to generated artifacts                                                                         | Both                                                    | [Enable optional OIDC](#enable-optional-oidc)                                      |
| `OIDC_GROUPS_CLAIM`             | `atlas.auth.oidc` group-claim name; string                                                         | `groups`; optional when OIDC is enabled                                                                                                           | Not secret                                                                                                                                      | Both                                                    | [Enable optional OIDC](#enable-optional-oidc)                                      |

## How configuration is resolved

Compose reads `--env-file` for interpolation and passes `core/backend/.env` to
backend-facing services. Explicit `environment` entries take precedence. For
example, containers use the Compose service hostname `postgres` instead of
`DJANGO_DATABASE_HOST=localhost` from the file.

Atlas loads Django settings at process startup. It validates and resolves plugin
configuration at that point. `OIDC_CLIENT_SECRET` is represented as a secret
reference, resolved in memory, and excluded from the frontend's public
configuration and generated distribution artifacts.

For a composed distribution, environment variables supply secret values only.
Provider selection, default behavior, provisioning, source binding, lifetimes,
origins, outbound trust, password policy, and recovery policy come from the
validated manifest and lock. See the [manifest reference](../reference/distribution-manifest.md#authentication).

## Common configuration failures

| Symptom                                                                | Check                                                                                                                                                                 |
|------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `DisallowedHost` or a rejected request through the gateway             | Add the request hostname to `DJANGO_ALLOWED_HOSTS`.                                                                                                                   |
| CSRF failure during sign-in or a mutation                              | Match the complete browser origin in `DJANGO_CSRF_TRUSTED_ORIGINS`.                                                                                                   |
| Backend cannot reach PostgreSQL in Compose                             | Do not change `DJANGO_DATABASE_HOST` to `localhost`; Compose supplies `postgres`.                                                                                     |
| OIDC is offered but cannot complete                                    | Confirm discovery URL and expected issuer are distinct, exact values; verify the registered Atlas callback and inspect the safe authentication troubleshooting guide. |
| Gateway starts on an unexpected port                                   | Check `ATLAS_PORT` and the `docker compose … ps` port mapping.                                                                                                        |
| An API's `spec_url` that used to resolve now shows `specResolveFailed` | Resolution now requires HTTPS and a publicly-routable address; add the host to `ATLAS_APIS_SPEC_URL_ALLOWLIST` if it's intentionally internal or HTTP-only.           |

For deployment, see [Production-like topology](../deployment/production.md).
For routine service work, see [Operations](../deployment/operations.md). To
change what Atlas includes, see [Assembling a distribution](distributions.md).
