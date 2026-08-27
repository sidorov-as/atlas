---
title: Register and ingest a repository
description: Configure a git source, register a repository through Django admin, run catalog-info.yaml discovery, and verify reconciliation.
audience:
  - catalog-user
  - operator
page-type: task
---

# Register and ingest a repository

Atlas Ingestion finds every `catalog-info.yaml` in a registered repository on
any git host reachable over HTTPS or SSH (GitHub, GitLab, Bitbucket, Gitea, or
any other git server), validates supported documents, and reconciles accepted
records into the catalog. Sources (connection and credential details for a git
host) are deployment-level manifest configuration; repositories are registered
and conflicts reviewed in Django admin. The current distribution has no
catalog page for either task.

## Outcome

Configure a source, register a repository against it, run ingestion, and
confirm that the resulting entity is YAML-managed with the expected metadata
and relations.

## Prerequisites

- The running distribution selects `atlas.ingestion`, Standard Catalog, and
  the kind plugins needed by the manifest.
- You have Django admin access to `/admin/`. Repository records have no
  separate Ingestion permission id.
- The distribution's manifest declares an `atlas.ingestion` source for the git
  host you intend to register a repository against (see below). No ingestion
  credential is ever entered through Django admin or stored in the database.
- The repository has one or more files named `catalog-info.yaml`. The checked-in
  parser recursively discovers that exact filename.
- Referenced owner Teams and parent Systems already exist, or the manifests
  declare them in an order that lets their refs resolve during the pass.

The [runnable Gitea ingestion example](https://github.com/sidorov-as/atlas/tree/main/examples/ingestion)
provisions a source, fixture repositories, and owner Groups, then runs a pass
automatically at startup — use it to see the whole flow end to end before
registering a repository against a real git host.

## 1. Configure a source

Sources are declared in the distribution manifest, not through Django admin,
so the set of reachable git hosts is fixed at deploy time. Add an entry to
`atlas.ingestion`'s `sources` list:

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

`id` is the value repositories reference as `source_id`. `authKind` is
`basic`, `bearer`, or `ssh-key`; `basic` and `bearer` credentials are sent as
request headers, never embedded in the clone URL. `credential` is a secret
reference — `{fromEnv: VAR}` for a single-line token, or `{fromFile: <path>}`
for multi-line material such as an `ssh-key` source's private key — resolved
once at process startup, never a value typed into Django admin.

An `ssh-key` source also requires host-key verification: either a
`knownHosts` secret reference (content or a mounted file path) or an explicit,
development-only `acceptUnknownHostKeys: true`. A source with neither fails
composition immediately rather than allowing an unverified connection later.

A plaintext `http://` `baseUrl` is rejected unless it targets loopback and
`allowDevelopmentHttp: true` is set — the same development-only escape hatch
other Atlas providers use.

## 2. Register the repository

Open `/admin/`, then open **Registered repositories** and select **Add
registered repository**. Enter:

| Field | Value |
| --- | --- |
| Source id | The `id` of a source declared in `atlas.ingestion` config, for example `gitea-primary` |
| Path | The repository's path relative to that source's `baseUrl`, for example `example-org/payments` |
| Default branch | The branch to inspect; defaults to `main` |

Django admin rejects the save if `source_id` does not match a currently
configured source, or if `path` is empty, begins with `/`, contains a `..`
segment, contains control or whitespace characters, or contains `://`. Save
the record. The current distribution has no catalog `Location` entity or
frontend registration form.

## 3. Prepare a manifest

Put a supported document in `catalog-info.yaml`. It must use the Atlas API
version, a supported kind, metadata name, and the kind's required spec fields.
For example, a System needs an owner Group reference:

```yaml
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: payments
  title: Payments
spec:
  owner: group:payments-team
```

See the [catalog-info.yaml concept](../concepts/catalog-info-yaml.md) for the
full schema model. On each successful run, the repository's current document
defines the entire YAML-managed entity. It does not patch manually edited
fields.

## 4. Run one ingestion pass

The `ingestor` service normally schedules discovery. To run an immediate,
one-off pass in the development topology, execute this from the repository
root:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml exec backend python manage.py ingest
```

This command processes every registered repository and refreshes URL-sourced
API specifications before it exits. The production-like topology uses the same
`exec backend python manage.py ingest` suffix with `docker-compose.yml`'s
compose invocation.

To confirm the scheduled worker is present, run:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml ps ingestor
docker compose --env-file core/backend/.env -f docker-compose.dev.yml logs ingestor
```

Atlas has no dedicated run-status screen or durable per-repository run history.
Use the command output and `ingestor` logs as execution evidence, then inspect
the reconciled entity.

## 5. Verify successful reconciliation

1. Open the relevant catalog list and search for the manifest's machine name.
2. Open the full detail page. Confirm the information banner says it is
   managed by `catalog-info.yaml` and names the registered repository.
3. Confirm the metadata, owner, System, and kind-specific fields match the
   manifest. The manual **Edit**, **Remove**, and **Revive** actions must be
   absent.
4. Open **Relations**. Confirm the owner/containment relations and any
   declared Architecture Relationships that resolve to known targets.
5. In Django admin, inspect **Conflict records**. No active record for the
   entity ref should remain after an uncontested successful claim.

If a repository no longer declares one of its YAML-managed entities, the next
pass marks the entity removed. Declaring the same ref again in that repository
revives the same entity identity.

## Common problems

### The repository is registered but no entity appears

Check the `ingestor` logs and run the one-off command to see connection,
parsing, unresolved-reference, or claim warnings. Confirm the filename is
exactly `catalog-info.yaml`, the default branch is correct, `source_id`
matches a currently configured source, and that source's credential can read
the repository.

### A manifest is rejected while other documents succeed

Failures are isolated by repository, file, and document. Correct the reported
document and run the command again. A successful process exit does not confirm
that every document was accepted.

### The detail page is read-only

Successful YAML management makes the detail page read-only. Change the
manifest and rerun ingestion instead of using a manual PATCH or catalog form
edit.

### The repository cannot be unregistered later

Any active or removed entity still claimed by it blocks deletion of the
repository record. See [Troubleshoot repository ingestion](troubleshoot-ingestion.md)
for the safe cleanup path.

## Next steps

- [Troubleshoot repository ingestion](troubleshoot-ingestion.md) for validation,
  claim, and retry failures.
- [Choose the correct entity workflow](choose-entity-workflow.md) before
  changing a YAML-managed record.
- [Inspect entity details](inspect-entity-details.md) to read reconciled
  relations and status indicators.
- The [runnable Gitea ingestion example](https://github.com/sidorov-as/atlas/tree/main/examples/ingestion)
  for a complete disposable manifest, Gitea bootstrap, and smoke test.
