# Discovery heuristics

Look for evidence, then record the file and line for each candidate. These are heuristics, not rules: when
they conflict or run out, mark the candidate uncertain and ask. Skip generated code, `node_modules`, vendored
dependencies, build output, and test fixtures.

## Systems

A System groups components that serve one product or business capability. Candidates, in order of strength:
a top-level product name in the README or docs; one repository that holds one product; a monorepo's top-level
groups (`apps/`, `services/`, `packages/` that clearly belong together). Default for a single repository: one
System named after the product. Whether to split a monorepo into several systems is a structural question.

## Components

| Component `type` | Signals                                                                                                                                                                                                                                                                                   |
|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `service`        | Deployable that listens on a port or serves requests: a `Dockerfile` with `EXPOSE` or a server `CMD`; a web framework entry point (Django, FastAPI, Flask, Express, NestJS, Spring Boot, Gin, ASP.NET); a Kubernetes `Deployment` plus `Service`; a `docker-compose` service with `ports` |
| `website`        | Browser frontend: React, Vue, Angular, Svelte, Next.js, Nuxt with a build to static assets or an SSR server; `index.html` plus a bundler config                                                                                                                                           |
| `worker`         | Deployable with no inbound API that consumes jobs or runs on a schedule: Celery or RQ workers, Sidekiq, BullMQ consumers, Kafka or queue consumers, cron entry points, `CronJob` manifests, `worker:` lines in a `Procfile`                                                               |
| `library`        | Code published or imported but not deployed: a package manifest with publish metadata and no entry point or Dockerfile (`setup.py`/`pyproject.toml` library, `package.json` with `main` and no start script, a Go module with no `main`, a shared `libs/` or `packages/` folder)          |

A unit that is both an HTTP server and a job consumer is usually a `service`; ask if it is really two. For
`lifecycle`: default to `production` when there is deployment config, `experimental` when the README says
prototype or the project is a skeleton, `deprecated` only when the code says so; if unclear, ask.

Where to look: `Dockerfile`s, `docker-compose*.yml`, Kubernetes and Helm manifests, `Procfile`, CI deploy jobs,
`render.yaml`, `serverless.yml`, package manifests (`pyproject.toml`, `package.json`, `go.mod`, `pom.xml`,
`build.gradle`, `*.csproj`, `Cargo.toml`), and the README.

## Resources

Map infrastructure the code connects to or defines:

| Resource `type` | Signals                                                                                                                                               |
|-----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| `database`      | PostgreSQL, MySQL, MongoDB, SQLite-as-service, etc.: a `docker-compose` image, connection strings or `DATABASE_URL`, ORM settings, migrations folders |
| `cache`         | Redis or Memcached used for caching or sessions                                                                                                       |
| `queue`         | Kafka, RabbitMQ, SQS, Pub/Sub, NATS, Redis used as a job queue or broker; message brokers are Resources                                               |
| `bucket`        | S3, GCS, Azure Blob, MinIO: bucket names in config, storage SDK clients                                                                               |
| `cluster`       | Kubernetes or other cluster definitions the code deploys to, when the user cares to document them                                                     |

Redis serves several purposes; choose by how the code uses it (cache versus broker) and ask if both. Take the
resource name from config or compose service name (`orders-db`), and attach it to the System it belongs to.
Several components using one store share one Resource.

## APIs and specs

- OpenAPI/Swagger: `openapi.yaml|json`, `swagger.json`, framework-generated schema files committed in the repo.
- AsyncAPI: `asyncapi.yaml|json`.
- gRPC: `*.proto` files with `service` blocks.
- GraphQL: `*.graphql` or `schema.graphql`, code-first schema definitions.
- Route definitions without a spec file (`@app.get`, `router.get`, `@RestController`, controllers, URL confs):
  evidence that the component exposes an API; propose an API of type `openapi` with no spec and note that endpoints
  appear once a spec is attached. Do not reconstruct a spec by hand.

Each API belongs to a System, is provided by the Component that serves it, and may be consumed by others. Record
the spec file path when one exists, so the curator can attach it.

## Relationships

Evidence for `A -> B`:

- **HTTP or gRPC calls between components**: base URLs or service names in config and env files
  (`BILLING_URL`, `http://billing:8000`), generated clients, SDK wrappers, `docker-compose` `depends_on`.
  Interaction kind `synchronous`, technology `REST/HTTPS` or `gRPC`.
- **Messaging**: producers and consumers of a topic or queue. The component to the queue Resource, and the other
  component from it. Kind `asynchronous`, technology `Kafka`, `RabbitMQ`, and so on.
- **Data access**: a component with the connection string of a database, cache, or bucket. Component to Resource,
  kind `data-access`. In the Component's spec this is also the `dependsOn` list (references between entities
  versus an Architecture Relationship are both written by the curator).
- **API provide/consume**: a component implementing an API is `providesApis`; one calling it is `consumesApis`.

Prefer fewer relationships with evidence over many guesses. Mark each with its file and line.

## Endpoint and operation links

For each Component, look for call sites that hit a documented API:

- **HTTP client calls**: generated clients, `fetch`/`axios`/`requests`/`httpx` calls, SDK wrappers whose method and
  path are visible. Note the HTTP method and path template.
- **Messaging**: producers and consumers that name a topic, queue, or channel. `publish`/`send` is role `publisher`;
  `subscribe`/consumer is role `subscriber`.

Then match each call site against the catalog with `search_api_endpoints` (method and path) or
`search_api_operations` (channel and direction) within the API the Component consumes. Use the catalog's own values for
the plan's link row, and check `get_endpoint_consumers`/`get_operation_consumers` to mark existing links `unchanged`.
Show the call site as `path:line` for the reviewer only. A call site with no matching endpoint or operation is listed
as not determined; do not guess a near match. If the search tools are not available, skip link rows and say so.

## Evidence format

`path/to/file.ext:LINE` (a single representative line). For a component, cite the entry point or Dockerfile; for a
resource, the config or compose line; for a relationship, the line that shows the call or connection.
