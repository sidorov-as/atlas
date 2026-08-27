# HTTP API guide

Each running Atlas instance serves a generated, authenticated OpenAPI document for its REST API.
The document includes endpoints contributed by the plugins selected for that instance. This page
explains how to use it rather than duplicating it.

## Where to find it

A running Atlas backend exposes its own OpenAPI document. Open it while authenticated against
your deployment to see the endpoints provided by its selected plugins. For example, these
endpoints are always present:

- `GET /api/catalog-home-settings/`: the homepage's admin-editable "About this catalog" Markdown
  content. Read by any authenticated user; writes require a superuser.
- `GET /api/me/`: whether the current authenticated user is a superuser (`isAdmin`).
- `GET /api/diagrams/landscape/`: the catalog-wide System Landscape diagram. Returns SVG by
  default; accepts `format=png` and `download=1`.

Catalog title, tagline, logo, and icon are not served by an endpoint — they come from the
frontend's own `atlas.config.ts`; see [Catalog branding](../configuration/catalog-branding.md).

The same document includes entity-scoped diagram routes, generic entity CRUD routes, and
namespaced plugin endpoints such as Database Schema's `api/plugins/atlas.database-schema/...`.

## Why this isn't hand-authored

The available endpoints depend on the plugins selected by a distribution. APIs, C4, and Database
Schema each add routes, and a distribution may not include all of them. A hand-written reference
could diverge from a deployment when its plugin selection changes. Atlas generates the document
from the route registrations served by the running backend.

## Authentication

The OpenAPI document and the API it describes require an authenticated session. Atlas does not
provide an unauthenticated API surface to browse.

Use the normal local or OIDC browser sign-in flow to establish a session. Do not put a password
or token in a checked-in command. State-changing browser requests also need the CSRF protection
used by the running Django backend. Consult the generated OpenAPI document for your deployment's
security scheme, fields, and endpoint paths.

## Requests, lists, and errors

Atlas entity collections use the request parameters documented for each generated operation. Use
the pagination and filtering fields provided there instead of assuming a fixed page size or query
syntax. For a non-2xx response, check authentication and CSRF first, then the endpoint schema,
permissions, resource state, and validation error before retrying. Do not blindly retry a
destructive request.

For example, inspect your authenticated generated schema before calling the
catalog home settings operation:

```shell
curl --cookie "sessionid=<your-session>" \
  http://localhost:8000/api/catalog-home-settings/
```

This is a session-authenticated GET. Obtain cookies through the supported login flow and include
the CSRF header for writes. See [browse the catalog](../using-atlas/browse-catalog.md),
[permissions](../concepts/permissions.md), or the generated endpoint definition for the selected
distribution.
