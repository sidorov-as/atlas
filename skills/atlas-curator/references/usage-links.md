# Endpoint and operation links

A link records that a Service (a Component) calls an HTTP endpoint, or publishes or subscribes on an AsyncAPI
operation. Links are written with four tools, never through an entity's `spec` and never as an Architecture
Relationship. They need the `apis:write` scope.

| Tool                            | Does                                                      |
|---------------------------------|-----------------------------------------------------------|
| `link_endpoint_consumers`       | Service consumes endpoints                                |
| `unlink_endpoint_consumers`     | Remove those links                                        |
| `link_operation_participants`   | Service publishes or subscribes on operations (`role`)    |
| `unlink_operation_participants` | Remove one role's link                                    |

## When to link

Only after the API's specification is attached and its endpoints or operations are confirmed to exist (see
[api-specs.md](api-specs.md)). Links come last in the write order. A target that is not in the catalog cannot be linked.

## Addressing an item

Give exactly one form per item:

- **By id** when you already hold it from `search_api_endpoints` or `search_api_operations`: `endpointId`, or
  `operationId` with a `role`.
- **By natural key** when you know the call from code: `api` (an API ref), `method`, `path` for an endpoint; `api`,
  `channelAddress`, `direction` plus `role` for an operation. Take the values from the search results, not from
  your memory of the code.

`role` is `publisher` or `subscriber`. One Service may hold both on the same operation.

## Batching

Each call takes one Service and up to 200 items. Group links by Service and send one call per Service (more calls if
a Service has over 200). Do not send one call per link.

## Dedupe

Before linking, check the existing links with `get_endpoint_consumers` or `get_operation_consumers` and mark
existing ones `unchanged` in the summary. Re-sending is still safe: an existing link comes back `unchanged`.

## Reading statuses

The response has a `status` per item, in request order, and a count per status.

| Status                    | Meaning and action                                                                                       |
|---------------------------|----------------------------------------------------------------------------------------------------------|
| `created` / `removed`     | Done                                                                                                     |
| `unchanged`               | Link already existed (link) or was already absent (unlink)                                               |
| `not_found`               | No such endpoint or operation. Report it with the key you sent                                           |
| `ambiguous`               | An operation key matched several operations. Report the candidate ids and ask the user which one         |
| `conflict`                | Removed endpoint, operation owned by the Service's own document, or a link managed by ingestion. Report  |
| `invalid`                 | Malformed item (both forms, neither, partial key, missing role). Fix the item and resend only that one    |

Never retry a `not_found`, `ambiguous`, or `conflict` item with a guessed identifier or a different endpoint. List
them for the user with the reason. A request-level rejection (missing scope, unknown Service, not a Component, over 200
items) changes nothing.

## consumesAPI

Linking an endpoint adds the endpoint's API to the Service's `consumesAPI` if it is missing, reported per item as
`apiRelationCreated`. Mention it in the summary. Unlinking never removes it, and operation links do not touch the
Service's relations.

## Links managed by ingestion

A link with origin `yaml` comes from ingested manifests. The unlink tools report it as `conflict`. Do not try to remove it.

## Removing links

Call an unlink tool only when the user explicitly asked to remove specific links. First call it with `dryRun` true,
show the links that would be removed, and wait for confirmation before the real call. A plan that merely omits an
existing link is not a request to remove it: leave it and mention it.
