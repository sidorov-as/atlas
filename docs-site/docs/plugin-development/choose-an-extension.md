---
title: Choose an extension mechanism
description: Map the behavior or data your plugin adds to the Atlas contract that owns it.
audience:
  - plugin-author
page-type: guide
---

# Choose an extension mechanism

Choose the contract based on the shape of the change, not where it will be
displayed. A plugin may use more than one mechanism, but each one
should have one clear owner and a narrow reason to exist. This guide is the
starting point before the first-plugin tutorial; it does not replace the exact
contracts in the [plugin API reference](reference.md).

## Start with the thing you are adding

| If you need to add... | Choose... | Why | Next guide |
| --- | --- | --- | --- |
| A catalog record with its own identity, lifecycle, API, and permissions | **Entity Kind** | The Entity Service delegates kind-specific storage and validation to one registered handler. | [Entity kinds and facets](entity-kinds-and-facets.md) |
| Optional, plugin-owned data that only makes sense on an existing entity | **Facet** | The data has a separate model and lifecycle without changing the entity kind's details. | [Entity kinds and facets](entity-kinds-and-facets.md) |
| A route, navigation item, entity-detail tab, or home widget | A frontend **Contribution** | Frontend composition combines the declared UI contribution with the selected distribution. | [Frontend contributions](extension-points.md) |
| A semantic property that lets other plugins target compatible Entity Kinds | A kind **Capability** | A kind declares what it supports; consumers gate behavior by capability instead of hard-coding kind ids. | [Entity kinds and facets](entity-kinds-and-facets.md#declaring-what-a-kind-provides) |
| A reusable runtime service that another plugin may consume | A backend **Capability** | The consumer resolves a named, versioned contract and handles its availability without importing a sibling's internals. | [Backend collaboration](backend-collaboration.md#capabilities-and-unavailable-providers) |
| A plugin-owned integration surface with several interchangeable implementations | An **Extension Point** | The owner publishes a namespaced, versioned contract with collection, singleton, or keyed cardinality. | [Backend collaboration](backend-collaboration.md#publish-an-extension-point) |
| One narrow lookup or action on another plugin's data | A **direct contract** | A small function or owner-managed registry keeps the data-owning plugin responsible for its own models and business logic. | [Backend collaboration](backend-collaboration.md#direct-contracts-and-failure-isolation) |
| An operation that must be authorized | A declared **Permission**, alongside the mechanism above | Permission declaration and centralized policy evaluation protect the action; a permission is not a data or UI extension mechanism on its own. | [Permissions](../concepts/permissions.md) |
| Recurrent, plugin-owned work | A **scheduled job** | The plugin declares its job ids; enabled and disabled lifecycle state controls whether those jobs run. | [Ingestion feature guide](../features/ingestion.md#api-operations-and-extension-surface) |

## Decision rules

1. Does the subject need a first-class catalog identity, create/update/delete
   lifecycle, and kind-specific details? Use an Entity Kind. Do not use a
   Facet merely because a new table is convenient.
2. Is it optional data attached to a record that another kind already owns?
   Use a Facet. Its model and API remain owned by your plugin, while the base
   entity retains its identity and lifecycle.
3. Is the result a visible UI affordance? Add a frontend Contribution. Use a
   capability gate when it should apply to every compatible kind, and declare
   a permission when access needs enforcement.
4. Does another plugin need a stable service it can resolve by name, possibly
   with no provider selected? Publish or consume a backend Capability. Treat
   unavailable and failed resolution as distinct outcomes.
5. Does one owner need to select or collect implementations supplied by other
   plugins? Publish an Extension Point and document its id, version,
   cardinality, keys where applicable, and dependency direction. The
   Ingestion connector and parser registries are the current keyed example.
6. Is the collaboration a one-off, narrow operation whose implementation must
   stay with its data owner? Use a direct contract. For example, Ingestion
   calls the APIs plugin's spec-refresh function on its own schedule, and
   plugins can register API delete guards without importing each other's
   models. A single lookup does not need a generic capability or extension
   point.
7. Must the work run independently of an HTTP request? Use a scheduled job
   only when the plugin owns the schedule, failure handling, and operational
   verification. Declare its ids on the plugin descriptor so disabled plugins
   have their jobs paused. Atlas currently has this pattern in Ingestion;
   adding a new scheduler integration requires the same explicit distribution
   and lifecycle design.

## Cross-cutting responsibilities

Every choice still has boundaries that the mechanism does not solve for you:

- Register runtime Entity Kinds, permissions, capabilities, and
  plugin-owned extension implementations from `register_runtime()` after
  Django setup, never as import side effects.
- Declare `requires_plugins` when the contract cannot work without its owner;
  keep the dependency graph acyclic and let composition report duplicates or
  missing requirements before deployment.
- Put a permission check at the backend action. A hidden tab or disabled
  button is only user guidance, not authorization.
- Keep plugin models and ORM queries private. A sibling plugin calls a public
  contract rather than importing internal models or tables.
- Test the selected contract's failure path: unavailable capability, duplicate
  registration, denied permission, disabled plugin, or isolated job failure.

## Verify the choice

Before building a distribution, confirm that a reviewer can answer all of the
following:

1. What does the plugin own, and why is this mechanism narrower than the
   alternatives?
2. Which plugin provides or consumes each cross-plugin contract, and what
   happens when it is absent or disabled?
3. Which permission protects each state-changing or sensitive operation?
4. Which focused guide and [contract reference](reference.md) defines the
   exact declaration and test surface?

Next, follow [Build your first plugin](tutorial.md) for the current
source-backed walkthrough, or continue to the linked focused guide for the
mechanism you chose.
