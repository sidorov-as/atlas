---
title: Atlas
description: Learn what Atlas supports and find the first guide for your role.
audience:
  - evaluator
  - catalog-user
  - operator
  - plugin-author
  - contributor
page-type: landing
icon: lucide/rocket
---

# Atlas

Atlas is an extensible software catalog for tracking software, its owners, and
its relationships. Catalog records can include systems, components, resources,
APIs, teams, documentation, and relationships. Selected plugins add
architecture diagrams, database schemas, repository ingestion, and flows.

Use Atlas to maintain a shared catalog, operate a repeatable distribution, or
add organization-specific behavior through typed plugin contracts.

## What Atlas supports

An Atlas installation is a distribution: Core and the plugins an operator
selects in a versioned manifest. The composer validates the selection and
produces locked backend and frontend artifacts before the application starts.
The running server and browser do not download plugins.

| Part | Supported role |
| --- | --- |
| Core | Owns catalog identity, lifecycle, authorization, audit, and the shared entity-page structure. |
| Selected plugins | Add entity kinds, feature data, API routes, scheduled work, navigation, diagrams, editors, and other views through explicit contracts. |
| Running distribution | Serves a web catalog and backend APIs, runs ingestion work, and stores catalog state in PostgreSQL. |
| Deployment | Supports source-mounted development and immutable production-like Docker Compose topologies. |

The checked-in default distribution selects Standard Catalog, APIs, C4,
Database Schema, Ingestion, and Flows. See [System shape](concepts/system-shape.md)
for the runtime boundaries and [Features and
Integrations](features/index.md) for the behavior supplied by those plugins.

!!! note "Current deployment boundary"
    Atlas currently documents Docker Compose for development and
    production-like operation. The documentation does not claim production
    support for Kubernetes, horizontal scaling, or runtime plugin installation.

## Choose your path

### Use the catalog

Browse software ownership and relationships, inspect entity documentation and
feature data, or maintain catalog records.

Start with [Run Atlas and inspect the demo catalog](getting-started/index.md).
If you already have access to an Atlas instance, begin with [Using
Atlas](using-atlas/index.md).

### Operate Atlas

Configure an installation, choose its plugins, run migrations, verify health,
and diagnose the supported deployment topologies.

Start by [choosing a supported deployment topology](deployment/index.md), then
follow [Operating Atlas](operating-atlas/index.md).

### Build a plugin

Extend a distribution with backend or frontend behavior while keeping plugin
ownership and dependencies explicit.

Start with [Build your first plugin](plugin-development/tutorial.md), then use
[Plugin Development](plugin-development/index.md) to find the relevant
extension contracts.

## Learn or contribute

- [Overview](overview/index.md) describes Atlas's product and architecture
  boundaries for evaluators.
- [Concepts and Architecture](concepts/index.md) defines the catalog, identity,
  lifecycle, authorization, and composition models shared by every journey.
- [Reference](reference/index.md) is the entry point for exact manifests,
  configuration, plugin contracts, and HTTP APIs.
- [Project](project/index.md) covers repository and contribution material.
