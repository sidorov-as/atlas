# Flow model

> The flow tool schema (`create_flow` / `update_flow`) is the source of truth for fields. If this file and the
> schema disagree, follow the schema.

A flow is a named step graph attached to one System. Fields: `system` (a `system:` ref, existing), `name`,
`description` (up to 4096 characters), `documentation` (up to 1 MiB), `steps`, and layout settings
(`autolayoutEnabled`, `layoutDirection`, `layoutEngine`) that you leave at their defaults. Flow-level fields are
camelCase; fields **inside a step are snake_case**.

## Step fields

| Field         | Notes                                                                             |
|---------------|-----------------------------------------------------------------------------------|
| `id`          | required, unique in the flow; short kebab-case such as `submit-order`             |
| `title`       | display title                                                                     |
| `summary`     | short description                                                                 |
| `next_step`   | one transition: `{"id": "<step id>", "label": "<optional>"}`                      |
| `next_steps`  | a list of transitions of the same shape, for branches                             |
| `color`       | `success`, `danger`, `warning`, `info`, `utility`, `normal` (plain steps only)    |
| `icon`        | a `@gravity-ui/icons` component name; only a name returned by `search_flow_icons` |
| `type_label`  | chip text for a plain step; free text                                             |
| `position`    | `{x, y}`; leave out so autolayout places the step                                 |
| `label_theme` | **deprecated**; use `color` instead and never set `label_theme`                   |

Do not put `title` or `summary` on a step that has `entity_ref`, `query_ref`, `event_ref`, or `flow_ref`: its text
comes from the reference, and the save is rejected.

## Step kinds (at most one reference per step)

| Kind                 | Field            | Value                                                                                                                                      |
|----------------------|------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| Plain step           | none             | just `title`, `summary`, and styling                                                                                                       |
| Entity               | `entity_ref`     | ref of a system, component, resource, or API that exists, for example `component:billing-service`                                          |
| Endpoint (call)      | `query_ref`      | `{api, endpoint, method, path, summary?}`: the API ref, the endpoint id (UUID), and the method and path as found by `search_api_endpoints` |
| Operation (message)  | `event_ref`      | `{api, operation, direction, channel, summary?}` as found by `search_api_operations`                                                       |
| External participant | `external_label` | free text naming a party that is not in the catalog                                                                                        |
| Nested flow          | `flow_ref`       | the integer id of another flow (a navigation link, not an embedded copy)                                                                   |
| Link                 | `link_url`       | a well-formed `http` or `https` URL                                                                                                        |

A step may carry only one of `entity_ref`, `external_label`, `query_ref`, `event_ref`, `flow_ref`, `link_url`.

## Transitions and branching

- A transition points at another step's `id` in the same flow. Every target must exist.
- A step with one successor uses `next_step`; several successors use `next_steps`, each with a `label` that says
  when that path is taken ("Payment approved", "Payment declined").
- Paths rejoin when several steps point at the same step. Any number of transitions may target one step.
- The graph must be **acyclic**: no step may lead back to itself or to an earlier step. A step transitioning to
  itself is a cycle.
- A terminal step has no transition.

## Limits

- At most 500 steps.
- Step `id` values unique; non-empty strings.
- `link_url` must be absolute `http`/`https`.

## Validation

`validate_flow` (when available) takes the same body as `create_flow` plus an optional `flowId` and returns every
violation without saving. Fix all of them before saving. Check the same things yourself when it is missing: unique
ids, transitions to existing steps, no cycle, one reference per step, no title or summary on a ref-backed step, and
the limits.
