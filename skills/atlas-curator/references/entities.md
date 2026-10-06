# Entity reference (fallback)

> Use this file only when `describe_kinds` is unavailable, and tell the user it may be out of date. When
> `describe_kinds` exists, it overrides everything here. Re-check against it if a write is rejected.

Field names are camelCase in tool calls. Send only the fields listed; unknown keys are rejected, and
`relationships` is never accepted in `spec` (use the relationship tools).

## Common `metadata` (every kind)

| Field           | Required | Notes                                                                                                                                   |
|-----------------|----------|-----------------------------------------------------------------------------------------------------------------------------------------|
| `name`          | yes      | Identifier, unique per kind. Must not be empty and must not contain `/` or `:`. Kept in English (see [conventions.md](conventions.md)). |
| `title`         | no       | Display name, up to 255 characters.                                                                                                     |
| `description`   | no       | Up to 4096 characters.                                                                                                                  |
| `documentation` | no       | Longer text.                                                                                                                            |
| `tags`          | no       | List of strings, up to 100.                                                                                                             |
| `labels`        | no       | String-to-string map, up to 100 items.                                                                                                  |
| `links`         | no       | Up to 50 objects: `url` (required), `title`, `description`, `type`.                                                                     |

Entity references use `[kind:][namespace/]name`, for example `group:platform-team` or `system:payments`. Write
the kind prefix explicitly.

## System

Spec: `owner` (required, `group:` ref).

```json
{
  "kind": "System",
  "metadata": {
    "name": "payments",
    "title": "Payments",
    "description": "Card and invoice payments."
  },
  "spec": {
    "owner": "group:platform-team"
  }
}
```

## Component

| Spec field     | Required | Values / notes                               |
|----------------|----------|----------------------------------------------|
| `type`         | yes      | `service`, `website`, `library`, `worker`    |
| `lifecycle`    | yes      | `experimental`, `production`, `deprecated`   |
| `owner`        | yes      | `group:` ref                                 |
| `system`       | yes      | `system:` ref; the system must already exist |
| `providesApis` | no       | list of `api:` refs                          |
| `consumesApis` | no       | list of `api:` refs                          |
| `dependsOn`    | no       | list of `resource:` refs                     |

List fields are replaced on update, so read first and send the merged list.

```json
{
  "kind": "Component",
  "metadata": {
    "name": "billing-service",
    "title": "Billing service",
    "tags": [
      "python"
    ]
  },
  "spec": {
    "type": "service",
    "lifecycle": "production",
    "owner": "group:platform-team",
    "system": "system:payments",
    "providesApis": [
      "api:billing-api"
    ],
    "dependsOn": [
      "resource:billing-db"
    ]
  }
}
```

## Resource

| Spec field | Required | Values / notes                                    |
|------------|----------|---------------------------------------------------|
| `type`     | yes      | `database`, `cache`, `bucket`, `queue`, `cluster` |
| `owner`    | yes      | `group:` ref                                      |
| `system`   | no       | `system:` ref                                     |

A `database` Resource can also carry a database schema (SQL DDL), which is not a `spec` field. When the
`set_resource_schema` tool is present, call it with `resource` (`resource:<name>`), `dialect` (`postgresql`,
`mysql`, `mssql`) and `sourceSql`, after the Resource exists. A success means the SQL was saved: read
`parseStatus` and `parseError` and report a failed parse. For a large DDL file you can run shell commands on,
call `request_attach` with field `schema` and `params` `{"dialect": "..."}`, then run the returned command
(see [api-specs.md](api-specs.md#upload-link-for-large-files) for the flow). Both need `catalog:write`.

```json
{
  "kind": "Resource",
  "metadata": {
    "name": "billing-db",
    "title": "Billing database"
  },
  "spec": {
    "type": "database",
    "owner": "group:platform-team",
    "system": "system:payments"
  }
}
```

## API

| Spec field    | Required | Values / notes                                             |
|---------------|----------|------------------------------------------------------------|
| `type`        | yes      | `openapi`, `grpc`, `asyncapi`, `graphql`                   |
| `owner`       | yes      | `group:` ref                                               |
| `system`      | yes      | `system:` ref                                              |
| `specSource`  | no       | `none` (default), `inline`, `url`                          |
| `specUrl`     | no       | public HTTPS address when `specSource` is `url`            |
| `specContent` | no       | document text when `specSource` is `inline`; at most 2 MiB |

Details and verification in [api-specs.md](api-specs.md).

```json
{
  "kind": "API",
  "metadata": {
    "name": "billing-api",
    "title": "Billing API"
  },
  "spec": {
    "type": "openapi",
    "owner": "group:platform-team",
    "system": "system:payments",
    "specSource": "none"
  }
}
```

## Kinds you cannot write

Group and User are read-only over MCP. Endpoints and operations are derived from an attached API spec.
