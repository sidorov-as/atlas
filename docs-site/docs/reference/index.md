---
title: Reference
description: Look up exact Atlas configuration, catalog manifests, plugin contracts, and generated HTTP API definitions.
audience:
  - catalog-user
  - operator
  - plugin-author
  - contributor
page-type: landing
---

# Reference

Reference lists exact fields, identifiers, constraints, and contract entry
points for readers who know what they need to look up. Use the linked task and
concept pages for procedures and explanations of why a contract exists.

## Who this section is for

Use this section while authoring catalog data, configuring an installation,
implementing a plugin, or calling the HTTP API. It answers:

- which fields and values a catalog manifest accepts;
- which environment settings affect the supported topologies;
- where the public Python and TypeScript plugin contracts are defined; and
- where a running distribution publishes its exact HTTP endpoint schema.

## Start here

Choose the reference that owns the value you need. For unfamiliar Atlas terms,
start with the [Domain glossary](../concepts/glossary.md).

## Recommended path

1. [Domain glossary](../concepts/glossary.md): resolve terminology before
   looking up exact values.
2. [catalog-info.yaml reference](../concepts/catalog-info-yaml.md): author the
   common envelope, per-kind specs, and entity relationships.
3. [Environment variables](../configuration/environment-variables.md): look
   up runtime configuration and secret-handling expectations.
4. [Plugin contract reference](../plugin-development/reference.md): inspect
   the public Python and TypeScript extension surface.
5. [Authentication routes and diagnostics](authentication.md): look up the
   browser gateway, failures, and provider health response.
6. [API Reference](../api-reference/index.md): find the authenticated,
   generated OpenAPI document for the running distribution.

## Section boundary

Reference pages are for lookup. For sequential setup, catalog, or
plugin-development guides, use [Getting
Started](../getting-started/index.md), [Using Atlas](../using-atlas/index.md),
[Operating Atlas](../operating-atlas/index.md), or [Plugin
Development](../plugin-development/index.md) for an end-to-end task.
