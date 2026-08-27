---
title: Use feature-specific catalog views
description: Move from a catalog entity to the supported API, C4, database schema, Flow, and generated HTTP API views.
audience:
  - catalog-user
page-type: task
---

# Use feature-specific catalog views

Start from a catalog entity for context, then open the feature view for the
task at hand. Which views are available depends on the distribution. A missing
tab or navigation item usually means its plugin is not selected, or the entity
lacks the required capability.

## Outcome

Find the appropriate specialized view from a System, Component, Resource, or
API, along with the generated operations behind it.

## Prerequisites

- You are signed in and can open the relevant entity detail page.
- The applicable plugin is selected in the distribution: `atlas.apis`,
  `atlas.c4`, `atlas.database-schema`, or `atlas.flows`.
- You have read permission for the catalog entity. Feature-specific writes may
  require the owner or a plugin-specific permission.

## APIs and service dependencies

Open an API entity from an API list or a System's APIs tab:

1. Read Overview for catalog documentation, ownership, and System context.
2. Open Specification when resolved specification content exists. The tab
   can render OpenAPI and AsyncAPI; other supported types can be downloaded.
3. Open Operations. OpenAPI APIs list Endpoints; AsyncAPI APIs list
   Operations. From there, open the child detail page for request/response or
   message details, linked services, and consumer graphs.
4. Open Relations when the dependency is a catalog-level relationship
   rather than a specific Endpoint/Operation service link.

Components list their provided and consumed APIs in Overview, along with their
Resource dependencies. Follow the link before changing a dependency to make
the change at the intended API or Endpoint level.

See the [APIs feature guide](../features/apis.md) and the [generated HTTP API
reference](../api-reference/index.md). Use the OpenAPI document from the
running instance for API, Endpoint, Operation, and service dependency
operations.

## C4 diagrams

Use architecture diagrams to examine boundaries and relationships:

- Open a System and use System Context for surrounding actors and systems, or
  System Architecture for the System's internal composition.
- Open a Component and use C4 Diagram for its component view.
- Use Relations first when you need to distinguish derived catalog links
  from the authored Architecture Relationships that C4 uses for interaction
  modeling.

Authenticated users can view diagrams through the built-in evaluator. For
controls, downloads, rendering dependencies, and failure modes, see the [C4
feature guide](../features/c4.md). If the tab is missing, check that C4 is
selected and that the entity is a System or Component that supports diagrams.

## Database schemas

Open a Resource and use Schema to edit or inspect its database schema. Use ER
Diagram to inspect the rendered model. Every Resource has the schema-host
capability; whether it has a parseable schema or diagram content depends on
its current schema data.

Schema writes use the owning Resource's edit authority. Before editing, confirm
that the Resource is manual and active. Repository-managed or unavailable
Resources must use their authoritative workflow. See the [Database Schema
feature guide](../features/database-schema.md) for dialects, parse states, and
API behavior.

## Flows

Use Flows in Atlas's left navigation to model behavior that spans catalog
entities and API operations. The list includes System, Team, and text filters,
pagination, previews, and dedicated create and edit routes.

Start a Flow with its home System, then add entity, plain, external, Query, or
Event steps as needed. Flow writes are checked against the home System's owner
Group. A user who can browse a System may still be unable to create or edit its
Flows. Entity and API or operation references come from catalog data, so inspect
their detail pages before binding them.

Flows have their own feature and are not a tab on a System detail page. If the
navigation item is absent, ask the operator to select `atlas.flows`. Use the
[generated HTTP API reference](../api-reference/index.md) for the Flow
operations available in the running distribution.

## Verify the result

For the feature you selected:

1. Return to the source entity and confirm its owner and System context.
2. Open the feature tab or navigation item and confirm the expected content
   loads without a missing-plugin or unavailable-entity warning.
3. Follow at least one entity/reference link back to its canonical detail page.
4. After a write, reload the specialized view and, where applicable, the source
   entity's Relations or History tab. A transient UI result is not sufficient.

## Common problems

### A feature tab or navigation item is missing

The plugin may be unselected, the entity may lack the required capability, or
the feature may require data that is not available yet, such as resolved API
specification content. Ask an operator to review the active distribution.

### A specialized view is read-only or a write is forbidden

Read access and write authority differ. Check the entity's owner and source
banner, then review [Permissions](../concepts/permissions.md). YAML-managed
entities remain repository-authoritative when an adjacent feature view is
installed.

### The generated API operation is not present

The generated document includes only the selected plugins. Confirm that the
feature is selected and open the document on the same Atlas instance before
using a route from another environment.

## Next steps

- [Inspect entity details](inspect-entity-details.md).
- [Create or edit catalog entities](create-edit-entities.md).
- [Manage an entity's lifecycle](manage-entity-lifecycle.md).
