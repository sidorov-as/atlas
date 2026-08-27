---
title: Standard Catalog
description: The required catalog foundation for Systems, Components, Resources, Teams, Actors, relations, and lifecycle actions.
audience: [catalog-user, operator, plugin-author]
page-type: feature
plugin-id: atlas.standard-catalog
---

# Standard Catalog

`atlas.standard-catalog` is the required foundation plugin. It defines the
catalog entities used by optional features: Systems, Components, Resources,
Teams (the `group` kind), and Actors.

## Dependencies, enablement, and configuration

The plugin is selected by every usable Atlas distribution; composition rejects
a distribution that omits it. It has no plugin-specific configuration. The
catalog's general environment and identity configuration is documented in
[Operating Atlas](../operating-atlas/index.md).

## Permissions

Atlas's central policy evaluator determines read and edit authority for each
registered kind. Writes are scoped to the entity owner's Team, and read access
does not grant edit authority. Lifecycle actions have their own eligibility and
purge checks. See [create or edit entities](../using-atlas/create-edit-entities.md),
[lifecycle management](../using-atlas/manage-entity-lifecycle.md), and the
[permissions concept](../concepts/permissions.md).

## Core workflows

- Browse, search, filter, and open catalog entities with [Browse the
  catalog](../using-atlas/browse-catalog.md).
- Inspect owners, systems, relations, documentation, links, and lifecycle
  state with [Inspect entity details](../using-atlas/inspect-entity-details.md).
- Create and edit manual entities only when you hold the owning Team's edit
  authority. YAML-managed entities are changed in their source repository and
  reconciled through [repository ingestion](../using-atlas/ingest-repository.md).
- Remove, revive, delete, or purge only through the lifecycle workflow; a
  purge is irreversible and may be blocked by references.

Systems and Components declare `architecture.subject.v1`; Resources declare
`schema.host.v1`. Those capabilities let C4 and Database Schema attach without
hard-coding a kind name.

## API and operations

The plugin provides catalog CRUD and relation operations. Use the running
[generated HTTP API reference](../api-reference/index.md) for exact routes and
schemas. There are no plugin-owned scheduled jobs or plugin-specific secret
settings. Catalog persistence follows the normal migrations and backup
procedures in [Operating Atlas](../operating-atlas/index.md).

## Extension surface and limits

Plugin authors can add their own Entity Kinds, Facets, and capability-targeted
contributions; start with [Entity kinds and facets](../plugin-development/entity-kinds-and-facets.md).
The Standard Catalog does not make a repository-managed entity editable: its
authoritative source and claim state remain part of ingestion.

## Troubleshooting and next steps

If a write is denied, check the owner and policy. If an entity is read-only or
unavailable, inspect its source and lifecycle banner before changing it.
Follow [Using Atlas](../using-atlas/index.md) for tasks, [Concepts](../concepts/index.md)
for identity and lifecycle rules, and the [Plugin API reference](../plugin-development/reference.md)
for extension contracts.
