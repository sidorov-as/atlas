# Relationships

Architecture Relationships describe how entities interact (for example one component calling another). They are
separate from the references inside `spec` (`dependsOn`, `providesApis`, `consumesApis`).

## Where they go

Always through the relationship tools: `list_relationships`, `create_relationship`. The server rejects a
`relationships` key in an entity's `spec`, and older servers silently drop it, so never put them there. If the
relationship tools are missing, tell the user relationships cannot be created and ask whether to continue with
entities only.

## Fields

| Field             | Required | Notes                                                                                             |
|-------------------|----------|---------------------------------------------------------------------------------------------------|
| `source`          | yes      | ref of a System, Component, Resource, or API; the acting user needs write access to it            |
| `target`          | yes      | ref of any catalog entity; it must exist                                                          |
| `label`           | yes      | short verb phrase, 1 to 255 characters, in the content language, for example "Makes API calls to" |
| `technology`      | no       | for example `REST/HTTPS`, `gRPC`, `Kafka`, `PostgreSQL`                                           |
| `interactionKind` | no       | `synchronous`, `asynchronous`, `data-access`, or `manual` (default)                               |
| `tags`            | no       | list of strings                                                                                   |

Choosing the interaction kind: request/response calls (HTTP, gRPC) are `synchronous`; messages, events, queues,
and streams are `asynchronous`; reading or writing a database, cache, or bucket is `data-access`. Use `manual`
only when none fits. Always set a label, and the technology when the evidence shows it.

## Check for duplicates first

Call `list_relationships` for the source (it returns incoming and outgoing). If a relationship with the same
source and target already exists with an equivalent meaning, leave it and report it as `unchanged`. If it exists
with a different label or technology, show the difference and ask whether to update it (`update_relationship`).

## Origin

Each relationship has an origin, `manual` or `yaml`. A `yaml` relationship comes from an ingested manifest.
Never modify or delete it; the server rejects that anyway. Tell the user it is managed by ingestion.

## Deletion

You may call `delete_relationship` only for a `manual` relationship, only when the user explicitly asked to delete
that specific relationship, and only after they confirmed a dry-run summary of the deletion.

## Order

Create relationships last, after every entity they mention exists.
