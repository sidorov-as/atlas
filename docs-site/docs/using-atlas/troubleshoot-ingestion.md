---
title: Troubleshoot repository ingestion
description: Diagnose manifest validation, claim conflicts, adoption, repository removal, and safe ingestion retries.
audience:
  - catalog-user
  - operator
page-type: task
---

# Troubleshoot repository ingestion

Use this guide when a registered repository does not produce the expected
catalog entity or when an existing entity blocks a YAML claim. Ingestion
isolates errors per repository, file, and document, so diagnose the named
record rather than resetting unrelated catalog data.

## Outcome

Identify the failure in logs or Django admin, correct it in the authoritative
source, and rerun ingestion without overwriting an unrelated record.

## Prerequisites

- The repository is registered as described in
  [Register and ingest a repository](ingest-repository.md).
- You can inspect the development topology's backend/ingestor logs or the
  corresponding deployment logs.
- You can use Django admin to inspect **Conflict records** and **Ingestion
  issues**. Adoption and lifecycle actions require their own owner or Purge
  Grant permissions.

## 1. Collect evidence before changing data

Run a one-off pass from the repository root to reproduce the current state:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml exec backend python manage.py ingest
```

Then inspect the scheduler's output:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml logs ingestor
```

In `/admin/`, open **Conflict records** and filter active records by repository,
kind, or name. The record includes the reason and timestamps. For every other
per-path failure (fetch, parse, schema validation, and `Include` composition),
open **Ingestion issues** and filter active records by repository or path; see
[IngestionIssue and composition failures](#ingestionissue-and-composition-failures)
below. Atlas does not persist a separate, per-repository run-status object, so
command/log evidence and these two admin lists are the supported diagnostic
surfaces.

## 2. Correct validation and discovery failures

| Symptom in logs | Cause | Safe corrective action |
| --- | --- | --- |
| `Skipping repository ...: no connector registered for source_id` | The repository's `source_id` no longer matches any source declared in `atlas.ingestion` plugin config. | Correct the Registered repository's `source_id`, or re-add the missing source to the manifest; never add a credential to `catalog-info.yaml`. |
| `Failed to fetch` (clone/authentication error) | The source's credential, `baseUrl`, `path`, or default branch is wrong, or the repository is unreachable. | Correct the Registered repository record's `path`/`default_branch`, or the source's `credential`/`baseUrl` in the manifest. |
| `ssh-key source has neither known_hosts nor accept_unknown_host_keys configured` (composition failure) | An `authKind: ssh-key` source is missing host-key verification. | Add `knownHosts` (content or a mounted path) to the source, or set the development-only `acceptUnknownHostKeys: true`. |
| `Failed to parse` | The file is not valid YAML. | Correct YAML syntax, commit it, then rerun ingestion. |
| `Skipping invalid manifest document` | The document fails the kind schema or common envelope. | Correct the reported kind, metadata, required fields, or field value; consult [catalog-info.yaml](../concepts/catalog-info-yaml.md). |
| `unresolved reference` | An owner, System, API, Resource, or other ref cannot resolve. | Create or declare the target first and check its expected kind/name. |
| `Rejecting duplicate ref` | Two documents in the same repository declare the same `(kind, namespace, name)`. | Keep one authoritative declaration or rename one; Atlas rejects both duplicates rather than choosing one. |

Django admin itself rejects an unresolvable `source_id` or an unsafe `path` at
save time (see [Register and ingest a repository](ingest-repository.md)), so
those two failure modes normally surface before a pass ever runs; the first
row above covers the remaining case where a source is removed from the
manifest *after* a repository was registered against it.

After correcting a manifest, rerun the one-off command and verify the entity
detail page. A warning in one file does not roll back documents accepted from
other files or repositories.

## IngestionIssue and composition failures

Every failure in the table above — plus a failed `kind: Include` (see
[catalog-info.yaml: composing fragments](../concepts/catalog-info-yaml.md#composing-fragments-with-kind-include))
— is, in addition to being logged, recorded as an **Ingestion issue** in
Django admin, keyed by repository and path:

| Symptom in logs | Cause | Safe corrective action |
| --- | --- | --- |
| `Include document in ... has no spec.paths list` | The `Include` document is missing `spec.paths`, or it isn't a non-empty list. | Add a `spec.paths` list of explicit paths and/or globs to the `Include` document. |
| `Include path ... did not match any file` | An explicit path doesn't exist, or a glob matched nothing, in the including file's directory. | Correct the path/glob, or add the missing fragment file, then rerun. |
| `Include path ... is named catalog-info.yaml and would be ingested a second time by manifest discovery` | An included fragment's basename is `catalog-info.yaml`, which manifest discovery would also find on its own tree-walk. | Rename the fragment to anything other than `catalog-info.yaml`. |
| `Include cycle detected: ...` | A chain of `Include` documents revisits a path already in the current resolution chain. | Break the cycle — remove the `Include` entry that points back at an ancestor. |
| `Include path ... is not a safe repository-relative path` or `sourceSqlPath ... is not a safe repository-relative path` | The path is absolute, contains a `..` segment, or contains a control character. A symlink that resolves outside the checkout is refused the same way. | Use a path relative to the declaring file that stays inside the repository, and do not link to files outside it. |
| `... exceeds the configured maximum fetched-file size` | A fetched manifest, fragment, or SQL file is larger than `maxFetchedFileBytes`. | Split or shrink the file, or raise `maxFetchedFileBytes` in `atlas.ingestion` config if the size is legitimate. See [Fetch and parse limits](../features/ingestion.md#fetch-and-parse-limits). |
| `... is too complex to parse` | The YAML nests deeper than `maxYamlNestingDepth`. | Flatten the document, or raise `maxYamlNestingDepth` if it is legitimate. |
| `Include path ... exceeds the configured maximum Include recursion depth` or `... maximum of N total included files` | An `Include` chain is longer than `maxIncludeDepth`, or one run fetched more than `maxIncludedFiles` fragments. | Flatten the chain or reduce the number of fragments, or raise the limit in `atlas.ingestion` config. |

An `IngestionIssue` for a given `(repository, path)` mirrors `ConflictRecord`'s
self-clearing behavior: a recurring failure updates the same row's `message`
and `last_seen` instead of creating a new row per run, and the row is marked
`is_active=False` (not deleted) once that repository and path complete a
subsequent run without the failure that created it. Unlike **Conflict
records**, `IngestionIssue` has no `reason` enum — `message` is the same
human-readable string that already goes to the log — and it only tracks the
most recent problem for a path: two independent, simultaneous failures for
the same `(repository, path)` collapse to one row. The application log
remains the complete record of everything that happened in a run.

## Resolve claim conflicts

An active Conflict record means the incoming YAML declaration lost the claim
arbitration. Resolve it in the existing source. Do not create a second entity
with the same ref.

### `manual_entity`

An active manual entity already owns the ref. Choose one source of truth:

- Keep manual ownership: remove or rename the rival manifest declaration.
- Hand the entity to the repository: a member of the entity's owner Group or a
  superuser may call the generated **adopt** operation for a System, Component,
  Resource, or API with this body, where `repository` is the target Registered
  Repository's `source_id` and `path` joined with `/`:

  ```json
  {"repository": "gitea-primary/example-org/payments"}
  ```

  The operations are `POST /api/systems/{id}/adopt/`,
  `POST /api/components/{id}/adopt/`, `POST /api/resources/{id}/adopt/`, and
  `POST /api/apis/{id}/adopt/`. Use an authenticated, CSRF-aware API client
  and the running instance's [generated HTTP API reference](../api-reference/index.md)
  for the exact contract. Adoption is one-way: the next successful ingestion
  fully reconciles the record from its manifest.

### `other_repository`

Another repository already owns the YAML entity. Correct the rival declaration
or transfer repository ownership through an intentional source migration. An
already YAML-managed entity cannot be adopted again, and a manual PATCH cannot
take it over.

### `removed_entity`

A removed entity still reserves its ref. If the original record should remain,
restore its supported source: revive a manual entity or re-declare it from its
original repository. If the ref must be released permanently, follow
[Manage an entity's lifecycle](manage-entity-lifecycle.md) to purge the
removed record with a valid grant. Do not purge simply to retry an uncertain
manifest change.

When the same ref later ingests successfully, Atlas marks active conflicts for
that ref as resolved. Keep the historical record for audit context.

## Retry safely

There is no separate "retry this repository" control. Re-running
`python manage.py ingest` retries every registered repository, which is safe
when the correction is committed and the source/repository configuration is
stable.

Before retrying, make sure the correction is in the repository's selected
default branch. After retrying, verify the specific entity's metadata,
provenance banner, Relations tab, and active Conflict records. Do not retry by
manually editing a YAML-managed entity.

## Unregister a repository safely

Deleting a **Registered repository** from Django admin is blocked while it
claims any YAML-managed entity, whether that entity is active or removed. Atlas
does not cascade-delete entities or orphan them.

To remove a repository deliberately:

1. Inventory every entity that the repository still claims.
2. For each entity, either keep the repository registered, migrate its source
   through an intentional compatible workflow, or remove it and then purge it
   with the required grant.
3. Confirm no claimed entity remains, including removed ones.
4. Delete the Registered repository record in Django admin.

Historical Conflict records do not block unregistration. They retain the
repository full name after the repository link is removed.

## Common problems

### The command exits successfully but the entity is unchanged

Per-document failures are logged and skipped without failing every source.
Read the warnings, check the active Conflict records, and compare the manifest
ref with the existing entity's kind and machine name.

### Adoption did not make the manifest values appear immediately

Adoption only marks the manual entity as YAML-managed by that repository. Run
ingestion after confirming that the repository declares the exact same ref.

### Deleting the repository is blocked after Remove

Remove is soft deletion; the YAML claim remains. Purge each removed claimed
entity only when permanent deletion is intended and its active references no
longer block it.

## Next steps

- [Register and ingest a repository](ingest-repository.md).
- [Choose the correct entity workflow](choose-entity-workflow.md).
- [Manage an entity's lifecycle](manage-entity-lifecycle.md).
