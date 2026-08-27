# APIs

Optional; requires Standard Catalog. Adds the `api` Entity Kind, along with API-owned child data
that isn't itself a registered kind.

## Entity Kind

`api`, handled by `ApiKindHandler`. On create and update, it resolves the API's OpenAPI/AsyncAPI
spec document, either fetched from a URL or supplied directly, sharing that resolution logic
with the Ingestion plugin's periodic spec-refresh job.

## Plugin-owned child data

`Endpoint` and `Operation` (a synchronous/AsyncAPI equivalent of an endpoint) are plugin-owned
data belonging to an `api` entity, not registered Entity Kinds in their own right. They have no
independent identity outside the API that owns them, so they don't get the
automatic read/edit permission pair a registered kind gets for free; this plugin registers
explicit permissions for reading endpoints and operations, and for creating, reading, and deleting
the service-to-endpoint and service-to-operation usage links that record which services depend on
which parts of an API.

## Cross-plugin surface

- `due_for_spec_refresh()` is called by Ingestion's periodic job to refresh every URL-sourced
  API spec that's due for a re-check. The query, the fetch, and the save all stay inside this
  plugin; Ingestion never imports its models directly.
- A delete-guard registry: any plugin holding its own reference to an `api` entity (Standard
  Catalog's `Component.providesApis`/`consumesApis`) can register a check that runs before that
  API is deleted, without this plugin needing to import the registering plugin's models to find
  out who references it.

## Frontend

List, detail, and form pages for `api`, plus detail pages for `Endpoint` and `Operation`. The
entity detail tab this plugin contributes to `api` entities renders its endpoints and operations;
dedicated components render each endpoint's/operation's request and response schemas, and graph
which services consume or provide them.
