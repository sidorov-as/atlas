# catalog-info.yaml reference

The Ingestion plugin discovers files named `catalog-info.yaml` in every registered repository and
parses each as a `---`-separated sequence of documents. Each document declares one entity. This page
describes the manifest format; for how a document becomes (or fails to become) a
Catalog Entity, see [Life of an entity](life-of-an-entity.md). For registering a repository so
Ingestion scans it at all, see the [Ingestion plugin](../features/ingestion.md).

Every document shares the same envelope:

```yaml
apiVersion: atlas/v1alpha1
kind: Component            # System | Component | Resource | API | User
metadata:
  name: customer-portal    # required; not empty/whitespace-only; must not contain "/" or ":"
  title: Customer Portal
  description: Public-facing storefront
  documentation: |
    Markdown rendered on the entity's detail page.
  labels:
    team: storefront
  tags: [frontend, tier-1]
  links:
    - url: https://runbooks.example.com/customer-portal
      title: Runbook
      description: How to operate and recover the customer portal.
      type: runbook
spec:
  # kind-specific — see below
```

`kind: Group` is unsupported. Create a Group (Team) through Django admin; it cannot be declared in
a manifest.

Each `metadata.links` item has a required `url` and optional `title`, `description`, and `type`.
Use links for external operational resources such as runbooks, dashboards, wikis, whiteboards, and
service documentation. Re-ingestion replaces the complete declared link list.

## Per-kind `spec`

=== "System"

    ```yaml
    kind: System
    metadata:
      name: user-management
    spec:
      owner: group:platform            # required, must resolve to a group
    ```

=== "Component"

    ```yaml
    kind: Component
    metadata:
      name: customer-portal
    spec:
      type: website                    # service | website | library | worker
      lifecycle: production            # experimental | production | deprecated
      owner: group:platform            # required
      system: system:user-management   # required
      providesApis: []                 # api refs
      consumesApis: [api:billing-api]  # api refs
      dependsOn: [resource:bookings-db]  # resource refs
    ```

=== "Resource"

    ```yaml
    kind: Resource
    metadata:
      name: bookings-db
    spec:
      type: database                   # database | cache | bucket | queue | cluster
      owner: group:platform            # required
      system: system:user-management   # optional
      databaseSchema:                  # optional; requires atlas.database-schema
        dialect: postgresql            # postgresql | mysql | mssql
        sourceSqlPath: db/schema.sql   # resolved relative to this file's own directory
    ```

=== "API"

    ```yaml
    kind: API
    metadata:
      name: billing-api
    spec:
      type: openapi                    # openapi | grpc | asyncapi | graphql
      owner: group:platform            # required
      system: system:billing           # required
      specSource: url                  # none (default) | inline | url
      specUrl: https://example.com/openapi.json
      specContent: ""                  # used when specSource: inline
    ```

=== "User"

    ```yaml
    kind: User
    metadata:
      name: jane.doe
    spec:
      displayName: Jane Doe            # optional, defaults to ""
      email: jane.doe@example.com      # optional, defaults to ""
    ```

    A `User` document has no `relationships` field. Actors can be a relationship's *target* but
    cannot be its *source*.

A ref field (`owner`, `system`, `providesApis`, `dependsOn`, …) accepts either `kind:name` or a
bare `name` when the field's expected kind is unambiguous. See
[Entity references](entity-references.md) for the full grammar.

## Declaring relationships

System, Component, Resource, and API specs accept a `relationships` list. It produces
[Architecture Relationships](entity-references.md#architecture-relationship), separate from the
derived Relation edges produced by `owner`, `system`, and `dependsOn`:

```yaml
kind: Component
metadata:
  name: customer-portal
spec:
  type: website
  lifecycle: production
  owner: group:platform
  system: system:user-management
  relationships:
    - target: component:api-gateway
      label: Makes API calls to
      technology: REST/HTTPS
      interactionKind: synchronous      # synchronous | asynchronous | data-access | manual (default)
      tags: [runtime]
```

`target` may reference an entity declared later in the same file, in a different file in the same
repository, or one that already exists. Reconciliation runs only after every document in the
ingestion pass has been upserted. A document's declared `relationships` list replaces that
entity's prior YAML-origin relationships on the next run; it never touches relationships created
manually through the UI.

## Things that surprise people

!!! warning "Re-ingestion overwrites every field"
    Unlike a `PATCH` through the REST API, re-ingesting the same ref overwrites every field to
    match the manifest exactly. A field the file omits is reset to its default instead of retaining
    the value from a previous run.

!!! warning "A claimed ref may already belong to someone else"
    If the ref already belongs to a manually-created entity, or to a different repository's
    claim, ingestion silently skips that document, logs a warning, and records a `ConflictRecord`.
    See
    [Claim arbitration](life-of-an-entity.md#yaml-ingestion-and-claim-arbitration).

!!! note "Two manifests, one ref, same run"
    If two documents anywhere in the same repository's manifests declare the same
    `(kind, namespace, name)`, neither is upserted. This is checked before validation, so it
    isn't reported as a validation error.

## Validation constraints and complete example

`apiVersion` is `atlas/v1alpha1`; `metadata.name` is required, is stripped of
leading/trailing whitespace, must not be empty after stripping, and may not
contain `/` or `:`; required owner and system references must resolve to the expected
kind. Enum values shown beside each per-kind field are the accepted values.
The whole document is validated before it is reconciled; use the ingestion run
status and [troubleshoot repository ingestion](../using-atlas/troubleshoot-ingestion.md)
for a corrective workflow.

```yaml
apiVersion: atlas/v1alpha1
kind: Component
metadata:
  name: customer-portal
  title: Customer Portal
  tags: [frontend]
spec:
  type: website
  lifecycle: production
  owner: group:platform
  system: system:user-management
  consumesApis: [api:billing-api]
  dependsOn: [resource:bookings-db]
  relationships:
    - target: component:api-gateway
      label: Makes API calls to
      technology: REST/HTTPS
      interactionKind: synchronous
```

To discover and reconcile this file, follow [Register and ingest a repository](../using-atlas/ingest-repository.md).

## Composing fragments with `kind: Include`

A discovered `catalog-info.yaml` can pull in additional YAML fragments instead of declaring every
entity in one file. Add a document with `kind: Include` anywhere in the `---`-separated sequence,
interleaved with ordinary entity documents:

```yaml
kind: Include
spec:
  paths:
    - .manifests/db-catalog-info.yaml
    - .manifests/*.yaml
---
apiVersion: atlas/v1alpha1
kind: Component
metadata:
  name: payments-service
spec:
  type: service
  lifecycle: production
  owner: group:payments-team
  system: system:payments
```

An `Include` document is never validated as an entity — it is expanded before schema validation,
so it can never produce an "invalid manifest document" failure on account of its own `kind`.

Each `spec.paths` entry is:

- **Resolved relative to the including file's own directory**, not the repository root and not
  the top-level manifest when includes nest. `services/payments/catalog-info.yaml` including
  `.manifests/db-catalog-info.yaml` fetches `services/payments/.manifests/db-catalog-info.yaml`,
  regardless of where else in the repository that directory lives.
- **Glob-capable.** `.manifests/*.yaml` matches every file in that directory; every match is
  fetched, parsed, and folded into the same document pool as the file that declared the `Include`.
- **Recursive.** A fetched fragment may itself contain `kind: Include` documents, expanded the
  same way. Ingestion tracks the repository-relative paths already visited in the current
  resolution chain and rejects (rather than infinitely follows) a path that revisits one already
  in that chain.
- **Confined to the repository.** An entry that is absolute, contains a `..` segment, or contains
  a NUL or control character is rejected and reported as an `IngestionIssue` instead of being
  fetched. Before a file is read, Atlas also confirms that its resolved location stays inside the
  repository checkout, so a symlink that points outside the checkout is refused too.
- **Never named `catalog-info.yaml`.** Manifest discovery already walks the whole repository tree
  for that exact filename, so an included fragment named `catalog-info.yaml` would be ingested
  twice. Such a path is rejected rather than fetched.

An unresolved or empty path/glob, a fetch failure, a rejected cycle, or a rejected
`catalog-info.yaml`-named fragment only skips that one `Include` entry — the including document's
other entities, that `Include` document's other paths, and the rest of the repository's manifests
still ingest normally. Each of these is also recorded as an `IngestionIssue`; see
[Troubleshoot repository ingestion](../using-atlas/troubleshoot-ingestion.md#ingestionissue-and-composition-failures).

## Declaring a Database Schema source

A `Resource` manifest can declare `spec.databaseSchema` to keep that Resource's `DatabaseSchema`
Facet ([Database Schema](../features/database-schema.md)) in sync with a `.sql` file already in the
repository, instead of entering it by hand:

```yaml
kind: Resource
metadata:
  name: bookings-db
spec:
  type: database
  owner: group:platform
  databaseSchema:
    dialect: postgresql            # postgresql | mysql | mssql
    sourceSqlPath: db/schema.sql
```

`sourceSqlPath` is **resolved relative to the directory of the manifest file (or included fragment)
that declares it** — the same rule `Include`'s `spec.paths` uses, resolved independently. Ingestion
fetches that file's content itself and applies it to the Facet using the same parsing the Database
Schema plugin's own editor uses; re-ingesting with changed SQL updates the Facet in place, and
removing the `databaseSchema` block clears it. `sourceSqlPath` follows the same path rules as
`Include` entries: an absolute path, a `..` segment, a control character, or a symlink that leaves
the checkout is rejected and recorded as an `IngestionIssue`. Declaring it has no effect — the Resource's other
fields still ingest normally — when `atlas.database-schema` isn't selected for the distribution. A
fetch failure or an invalid declaration is isolated to that Resource and recorded as an
`IngestionIssue`, the same as any other per-manifest failure.

Once a Resource is YAML-managed, its Facet can no longer be edited by hand through the Database
Schema plugin's own editor — see [Database Schema: repository-managed
schemas](../features/database-schema.md#repository-managed-schemas).
