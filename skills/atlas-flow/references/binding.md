# Binding steps to the catalog

For each step decide what it refers to. Check the catalog; do not guess, and never bind to something you have not
confirmed exists.

## Entities

1. Search with `search_catalog` using the name the user used (`q`), filtered by `kind` when it is clear (component,
   resource, api, system).
2. If there is one clear match, confirm it with the user in a short question that shows its `ref` and title, then
   set `entity_ref` to the returned `ref`.
3. If there are several plausible matches, ask which one. If none, treat the party as missing (see below).
4. Use `get_entity` when you need to disambiguate (owner, system, description).

A step bound to an entity has no `title` or `summary`; the entity supplies the text. If the user wants a
description of what happens in that step, put it on a plain neighbor step or in the flow's `documentation`.

## Endpoints (the step is an HTTP call)

1. Identify the API: search the catalog for the API (`kind: api`), then use `search_api_endpoints` with the API's
   id (`apiId`) and a query for the path or action.
2. Pick the endpoint that matches the call. When several look right, show method and path and ask.
3. Set `query_ref` to `{api, endpoint, method, path, summary}` using the values returned: the API ref, the endpoint
   id, and the method and path exactly as returned.

If the endpoint tools are missing, bind to the API's component with `entity_ref` instead and say you cannot bind to a
specific endpoint.

## Operations (the step is a message or event)

Same as endpoints, with `search_api_operations`: set `event_ref` to `{api, operation, direction, channel, summary}`
from the result.

## Other flows

For "then the refund process starts", find the flow with `list_flows` and set `flow_ref` to its integer id. Do not
copy its steps.

## Participants missing from the catalog

When a person, system, or service is not in the catalog (or the user does not want it there), record the step with
`external_label` set to a clear name, for example the external vendor's name. Keep the dialogue moving; do not stop
to create entities. Remember it as an unbound step and handle it as in [unbound-steps.md](unbound-steps.md). A
genuinely external party (a payment provider, an end user) stays external, and is not offered for documentation
unless the user wants it in the catalog.

## Plain steps

A step that is an action, decision, or outcome with no participant to bind ("Check stock", "Order rejected") is a
plain step with `title`, optional `summary`, optional `color` and `icon`.
