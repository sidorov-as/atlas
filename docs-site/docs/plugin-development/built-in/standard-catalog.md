# Standard Catalog

Every distribution must select this plugin. Core registers no concrete Entity Kind;
Standard Catalog provides `System`, `Component`, `Resource`, `Team`, and `Actor`.

## Entity Kinds

| Kind | Notes |
| --- | --- |
| `system` | Declares `architecture.subject.v1` and appears as a diagrammable subject wherever that capability is checked. |
| `component` | Also declares `architecture.subject.v1`; carries `providesApis`/`consumesApis` references used by the APIs plugin. |
| `resource` | Declares `schema.host.v1`, the attachment point for the Database Schema plugin's Facet and tabs. |
| `group` (Team) | Groups of Actors. |
| `actor` | Declares `architecture.actor.v1`; the Catalog Entity representing a person, independent of login. |

Each kind has its own handler (`system_handler.py`, `component_handler.py`, `resource_handler.py`,
`group_handler.py`, `actor_handler.py`) implementing the same `EntityKindHandler` contract
described in [Entity kinds & facets](../entity-kinds-and-facets.md).

## Frontend

List, detail, and form pages for every kind it owns (`SystemsListPage`/`SystemDetailPage`/
`SystemFormPage`, and the same trio for Components, Resources, and Teams), plus the overview tab
each of those kinds contributes to the shared entity detail shell.

## Cross-plugin surface

Standard Catalog exposes `add_consumed_api`, which lets the APIs plugin record
that a `Component` consumes a given `API`. It is a single ORM-backed edge exposed as a function
call because an explicit user action triggers the direct write; it is not resolved dynamically at runtime.
