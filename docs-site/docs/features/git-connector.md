---
title: Git connector
description: Configure the built-in provider-agnostic Git source connector used by Atlas Ingestion.
audience: [catalog-user, operator, plugin-author]
page-type: feature
plugin-id: not-applicable
---

# Git connector

`GitConnector` is the source connector built into `atlas.ingestion`. It finds
every `catalog-info.yaml` in a registered repository by performing a shallow
(`depth=1`, single-branch) clone over HTTPS or SSH, then reads files straight
from that local checkout. It works identically against GitHub, GitLab,
Bitbucket, Gitea, or any other git host reachable over one of those
transports — there is no provider-specific REST integration or code path.

Cloning uses `dulwich` (a pure-Python git implementation) with SSH backed by
`paramiko`; neither transport ever invokes a subprocess `git` or `ssh`
binary, which closes the `ext::`-transport and SSH-argument-injection
command-injection classes by construction rather than by allowlisting.

## Prerequisites and configuration

Enable [Ingestion](ingestion.md), then declare one or more sources in
`atlas.ingestion` plugin config — deployment-level connection and credential
details for a git host, resolved once at process startup, never entered
through Django admin or stored in the database:

```yaml
plugins:
  - id: atlas.ingestion
    config:
      sources:
        - id: gitea-primary
          baseUrl: https://gitea.example.com
          authKind: bearer
          credential:
            fromEnv: GITEA_INGESTION_TOKEN
```

`authKind` is `basic`, `bearer`, or `ssh-key`. `basic` and `bearer`
credentials are sent as request headers, never embedded in the clone URL.
`ssh-key` sources also require host-key verification: either a `knownHosts`
secret reference or an explicit, development-only
`acceptUnknownHostKeys: true`; a source with neither fails composition
immediately rather than allowing an unverified connection later. Register a
repository against a source by its `id` and the repository's `path` relative
to that source's `baseUrl` — see [Register and ingest a
repository](../using-atlas/ingest-repository.md).

## Verify and operate

After ingestion runs, inspect the repository run status and resulting entity
provenance. Successful discovery lists only files named
`catalog-info.yaml`; it does not ingest arbitrary YAML. See [Register and
ingest a repository](../using-atlas/ingest-repository.md) for the supported UI
and reconciliation verification.

## Failures and safe actions

A clone failure means the source's credential, `baseUrl`, or the
repository's `path`/default branch is wrong, or the repository is
unreachable; correct the Registered Repository record or the source's
manifest configuration. An `ssh-key` source that fails composition is
missing host-key verification (`knownHosts` or `acceptUnknownHostKeys`).
Correct a failed manifest in the repository; do not edit its managed Atlas
entity. Inspect the run record and follow [ingestion
troubleshooting](../using-atlas/troubleshoot-ingestion.md).

## Extension and limits

`GitConnector` is the only built-in connector, but it is provider-agnostic —
adding a new git host is a manifest change (a new `sources` entry), not a
plugin change. A host reachable only over an unsupported transport (for
example anonymous `git://` or `file://`) would require a plugin
implementation of Ingestion's connector contract; see [extension
points](../plugin-development/extension-points.md). Use [repository
ingestion](../using-atlas/ingest-repository.md), [Operating
Atlas](../operating-atlas/index.md), the [catalog manifest
concept](../concepts/catalog-info-yaml.md), [extension
points](../plugin-development/extension-points.md), and the running [generated
HTTP API reference](../api-reference/index.md) for repository operations.

The [runnable Gitea ingestion example](https://github.com/sidorov-as/atlas/tree/main/examples/ingestion)
contains a complete disposable source, fixture repositories, and bootstrap.
