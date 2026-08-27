# Architectural principles

These decisions shape everything else in this section: why plugins are isolated
the way they are, what happens when composition or a plugin fails, and how upgrades and removals
stay safe.

## Plugins collaborate only through declared contracts

Plugins declare required and optional Plugin Releases in their manifests. They collaborate only
through named, versioned capability contracts and typed extension points. They do not import
another plugin's implementation, read its tables directly, or hold a foreign key into its models.
A plugin may publish its own namespaced, versioned extension points for other plugins to use.
Ownership and ordering come from an explicit, acyclic manifest dependency graph. A contract-only
package can expose the relevant types without an implementation; the ingestion plugin's connector
and parser extension points work this way. This requires contract and dependency-resolution
machinery, so a missing optional plugin or swapped capability provider is handled explicitly.

A plugin cannot delete, replace, or wrap another plugin's contributions. The deployment
configuration controls disabling a contribution, ordering a collection, and selecting which
implementation fills a singleton extension point.

## Every entity kind renders into the same canonical shell

Every Entity Kind's detail route renders the same core-owned shell. Kind-specific and cross-plugin
content arrive as typed header, action, banner, and tab contributions to that shell. A plugin may
add an entirely separate custom route, such as a full-screen diagram editor, but it cannot replace
the canonical shell. This keeps permissions,
Unavailable Entity handling, and additions like a diagram tab or a schema tab composing
consistently no matter which plugins are selected.

## Authorization is centralized across plugins

Plugins declare stable, namespaced permission ids and ask a single Authorization Service for a
decision. Backend enforcement is authoritative, while a frontend check only shapes what is shown.
Authentication alone never grants access. A deployment selects one policy evaluator, such as
built-in role-based access control or an external policy engine. Plugins cannot create a parallel
role system.

## Composition and runtime failures have different scopes

Atlas refuses to start when the selected plugin graph, its configuration, its imports, its
artifacts, or its migrations are invalid. It does not silently quarantine part of a broken
deployment. After that check passes, a problem in one contribution, request, capability call, or
background job is isolated to that piece and reported as degraded health. Composition prioritizes
consistency; a running deployment prioritizes resilience.

## Removing a plugin is reversible by default

Removing a Plugin Release does not automatically reverse its migrations or delete its data. Its
Catalog Entities become generic, read-only Unavailable Entities. Relationships stay intact, and
its tables remain in place for a compatible reinstall. Destroying that data requires a separate,
explicit action while the plugin's code is still present and able to validate the removal. It is
never an automatic side effect of taking a plugin out of a distribution.

## Upgrades follow expand-contract

A plugin's migrations and APIs stay compatible with the previous deployed release throughout a
rolling upgrade. Schema expansion ships and rolls out before the backend and frontend that depend
on it, and destructive changes are contracted only in a later release. The migration safety check
described in [Operations](../deployment/operations.md) enforces this by default. An operator who
needs an incompatible, single-step upgrade must explicitly opt into maintenance mode.

## Core, plugins, and distributions version independently

Core, the Plugin API contract, every Plugin Release, and every Distribution carry independent
version numbers connected by declared compatibility ranges and a reproducible lock. A release
train can still update several of them together when useful. A focused fix to one plugin does not
require bumping everything else it ships alongside.
