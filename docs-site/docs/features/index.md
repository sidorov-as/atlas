---
title: Features and Integrations
description: Find the installed product behavior contributed by Atlas's built-in plugins and their external integration points.
audience:
  - catalog-user
  - operator
  - plugin-author
page-type: landing
---

# Features and Integrations

Plugins selected when a distribution is built provide Atlas features. This
section explains each catalog capability, its dependencies, how people use it,
how to operate it, and how to extend it.

## Who this section is for

Use this section if you use an installed feature, operate its supporting
services, or want a built-in plugin example. It covers:

- what each documented built-in plugin provides;
- the other plugins or services it depends on;
- user and operator concerns for the feature; and
- implementation contracts that plugin authors can reuse.

## Start here

Begin with [Standard Catalog](standard-catalog.md)
for the shared Systems, Components, Resources, Teams, ownership, relations, and
lifecycle surface used by the other feature areas.

## Recommended path

1. [Standard Catalog](standard-catalog.md): the
   common catalog foundation.
2. [APIs](apis.md): API specifications,
   endpoints, operations, and dependency links.
3. [C4](c4.md): landscape and entity-scoped
   architecture diagrams.
4. [Database Schema](database-schema.md): SQL
   schema data and ER diagrams attached to Resources.
5. [Ingestion](ingestion.md): repository discovery, parsing, claims, and
   reconciliation.
6. [Flows](flows.md): process documentation across catalog entities and API
   operations.
7. [Git connector](git-connector.md): the built-in, provider-agnostic
   repository source integration used by Ingestion.
8. [MCP](mcp.md): a curated, PAT-authenticated HTTP API for MCP tool-calling
   clients such as Claude Desktop.
9. [Catalog authoring skills](mcp-skills.md): install skills that let an
   assistant fill the catalog from code and build flows through MCP.

## Section boundary

Feature pages describe behavior available when the corresponding plugin is
selected in a distribution. For catalog-wide tasks, see [Using
Atlas](../using-atlas/index.md). For plugin selection, see [Operating
Atlas](../operating-atlas/index.md). For implementation contracts, see [Plugin
Development](../plugin-development/index.md).
