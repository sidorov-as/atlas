---
title: Ingestion
description: Configure git sources, register repositories, discover catalog-info.yaml, and reconcile repository-managed catalog entities.
audience: [catalog-user, operator, plugin-author]
page-type: feature
plugin-id: atlas.ingestion
---

# Ingestion

`atlas.ingestion` discovers `catalog-info.yaml` files in registered
repositories, on any git host reachable over HTTPS or SSH, and reconciles
their entities into the catalog. It requires `atlas.standard-catalog`, is
backend-only, and owns repositories, provenance, run history, retries,
conflicts, and reconciliation.

## Enablement and configuration

Select Ingestion with Standard Catalog. Its discovery and specification-refresh
jobs run on Atlas's shared scheduler (`manage.py runapscheduler`, the `ingestor`
service), which any plugin can contribute jobs to; Ingestion is not required for
the scheduler or for Atlas to run. The built-in connector is
provider-agnostic; declare a source (connection and credential details for a
git host) in `atlas.ingestion` plugin config, then register a repository
against it by `source_id` and `path`. Store credentials as secret references
(`fromEnv`/`fromFile`) resolved from the manifest and never put them in
`catalog-info.yaml` or a documentation example. See [Git
connector](git-connector.md).

### Fetch and parse limits

Ingestion reads files from repositories it does not control, so each fetch and parse is
bounded. The limits are optional fields of the `atlas.ingestion` plugin config; raise one only
when a legitimate repository needs it.

```yaml
plugins:
  - id: atlas.ingestion
    config:
      maxFetchedFileBytes: 5242880   # default: 5 MiB per fetched file
      maxYamlNestingDepth: 100       # default
      maxIncludeDepth: 50            # default: longest kind: Include chain
      maxIncludedFiles: 500          # default: Include files per ingestion run
```

| Field | Default | Bounds |
| --- | --- | --- |
| `maxFetchedFileBytes` | 5 MiB (`5242880`) | Size of any single file Ingestion fetches: a `catalog-info.yaml`, an `Include` fragment, or a `sourceSqlPath` file. The check runs before the content is parsed. |
| `maxYamlNestingDepth` | `100` | How deeply a fetched YAML document may nest. |
| `maxIncludeDepth` | `50` | The length of a chain of `kind: Include` documents that include each other. Cycles are rejected separately. |
| `maxIncludedFiles` | `500` | Files fetched through `Include` resolution in one ingestion run. Top-level `catalog-info.yaml` discovery does not count toward it. |

Every value must be greater than zero. A file or chain that exceeds a limit is skipped, the rest
of the repository still ingests, and the failure is recorded as an `IngestionIssue`; see
[Troubleshoot repository ingestion](../using-atlas/troubleshoot-ingestion.md#ingestionissue-and-composition-failures).
Paths declared in a manifest are confined to the repository checkout; see
[catalog-info.yaml: composing fragments](../concepts/catalog-info-yaml.md#composing-fragments-with-kind-include).

## Permissions and workflows

Register a repository, run ingestion or wait for it to start, then inspect the
run status and entity provenance. Correct `catalog-info.yaml` in the source
repository. Reconciled entities are read-only. For workflows, conflicts,
adoption, retries, and unregister constraints, see [Register and ingest a
repository](../using-atlas/ingest-repository.md) and [Troubleshoot repository
ingestion](../using-atlas/troubleshoot-ingestion.md).

## API, operations, and extension surface

Use the running [generated HTTP API reference](../api-reference/index.md) for
repository and run operations. Scheduled discovery and URL specification
refresh are also available. When a run fails, check the job and backend logs.
The plugin publishes connector and parser extension points,
`atlas.ingestion.connectors.v1` and `atlas.ingestion.parsers.v1`. Authors add
implementations through these contracts.

## Limits and troubleshooting

`GitConnector` is the only built-in connector — provider-agnostic, so adding
a git host is a manifest change, not a plugin change — and
`catalog-info.yaml` is the only built-in parser. A `catalog-info.yaml` can
compose in additional fragments via `kind: Include`; see [catalog-info.yaml:
composing fragments](../concepts/catalog-info-yaml.md#composing-fragments-with-kind-include).
A `Resource` manifest can also declare `spec.databaseSchema` to keep its
`DatabaseSchema` Facet in sync when `atlas.database-schema` is selected; see
[catalog-info.yaml: declaring a Database Schema
source](../concepts/catalog-info-yaml.md#declaring-a-database-schema-source).
Network, credential, clone-timeout, malformed-manifest, duplicate-reference,
and claim-conflict failures are reported in run state, and — along with
`Include` composition failures — recorded as an admin-visible
`IngestionIssue`. Fix the indicated source or access, then retry.
Repository-authoritative entities cannot be edited manually.

## Next steps

Read the [catalog manifest concept](../concepts/catalog-info-yaml.md),
[composition and operations](../operating-atlas/index.md), and [extension
points](../plugin-development/extension-points.md).
