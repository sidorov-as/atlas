---
title: Built-in registries
description: Lookup current built-in plugin ids and the namespaces used for Atlas extension identifiers.
audience: [plugin-author, operator]
page-type: reference
---

# Built-in registries

The default distribution selects `atlas.standard-catalog`, `atlas.apis`,
`atlas.c4`, `atlas.database-schema`, `atlas.ingestion`, and `atlas.flows`.
Their canonical feature pages describe product behavior and permissions.

| Registry | Identifier rule | Owner / lookup |
| --- | --- | --- |
| Entity kinds | Stable kind id | Standard Catalog owns core kinds; see [catalog manifest](../concepts/catalog-info-yaml.md). |
| Facets | Plugin-owned, attached to a kind | See [entity kinds and facets](../plugin-development/entity-kinds-and-facets.md). |
| Capabilities | Namespaced/versioned semantic id | `architecture.subject.v1` is used by C4. |
| Extension points | Namespaced/versioned id | Ingestion: `atlas.ingestion.connectors.v1`, `atlas.ingestion.parsers.v1`. |
| Frontend contributions | Stable plugin-owned contribution id | See [frontend contributions](../plugin-development/extension-points.md). |
| Permissions | `atlas.<plugin>.<resource>.<action>` | Register through the central permission registry. |
| Scheduled jobs | Descriptor `job_ids` | The plugin descriptor owns its job ids. |

Registry values are composition contracts. Users do not see them as labels.
Check the owning plugin source and its feature guide before depending on one.
Duplicate ids fail composition. See [backend collaboration](../plugin-development/backend-collaboration.md)
and [plugin permissions](../plugin-development/permissions.md).
