# catalog-ingestion Specification

## Purpose
Ingestion pipeline that discovers `catalog-info.yaml` manifests in registered repositories and upserts them into the catalog as entities, via a connector interface with a provider-agnostic `GitConnector` as the only v1 implementation.

## Requirements

### Requirement: Registered repository configuration
A Registered Repository SHALL hold `{source_id, path, default branch}` as operational config, managed via Django admin. `source_id` SHALL reference a source declared in `atlas.ingestion` plugin config; `path` SHALL be the repository's path relative to that source's `baseUrl`. No ingestion credential SHALL be stored on a Registered Repository or anywhere else in the database.

#### Scenario: Repository registered via admin
- **WHEN** an operator adds a Registered Repository through Django admin with a `source_id` and `path`
- **THEN** the ingestor includes it in the next discovery run, authenticating using the credential configured for that `source_id`

#### Scenario: Path is validated against URL injection
- **WHEN** an operator saves a Registered Repository whose `path` is empty, begins with `/`, contains a `..` segment, contains control or whitespace characters, or contains `://`
- **THEN** Django admin rejects the save with a validation error

#### Scenario: Unknown source is rejected
- **WHEN** an operator saves a Registered Repository whose `source_id` does not match any source currently declared in `atlas.ingestion` plugin config
- **THEN** Django admin rejects the save with a validation error naming the unresolved `source_id`

### Requirement: Manifest discovery via the connector interface
On each run, the connector SHALL list files matching `**/catalog-info.yaml` in each registered repository's default branch by performing a shallow, single-branch clone of that repository, and a single provider-agnostic `GitConnector` SHALL be the only v1 implementation of that interface, serving any source reachable over HTTPS or SSH.

#### Scenario: Discovery finds a nested manifest
- **WHEN** a registered repository contains `services/user-management/catalog-info.yaml`
- **THEN** the connector's `list_manifest_paths` includes that path

#### Scenario: Discovery works against a non-GitHub source
- **WHEN** a registered repository's `source_id` references a source whose `baseUrl` is a self-hosted Gitea, GitLab, or Bitbucket instance
- **THEN** discovery, fetch, and head-SHA resolution succeed identically to a `github.com`-backed source, with no provider-specific code path

### Requirement: Ingestion sources are deployment-level configuration, not database rows
`atlas.ingestion` plugin config SHALL declare a `sources` list, each with an `id`, `baseUrl`, `authKind` (`basic`, `bearer`, or `ssh-key`), and a `credential` resolved through the plugin configuration system's secret-reference mechanism. Sources SHALL be resolved once at process startup; a Registered Repository SHALL only ever reference a source by `id`, never embed or store a credential itself.

#### Scenario: Source credential never reaches the database
- **WHEN** an ingestion pass authenticates against a configured source
- **THEN** the credential used comes from the resolved plugin configuration, and no database row, migration, or admin form field ever holds that credential value

### Requirement: SSH sources require verified host keys
A source with `authKind: ssh-key` SHALL require either explicit known-hosts content/path or an explicit development-only opt-in to accept unknown host keys; it SHALL NOT silently trust-on-first-use, and a scheduled ingestion pass SHALL NOT block on an interactive host-key prompt.

#### Scenario: SSH source without host-key configuration fails closed
- **WHEN** a source declares `authKind: ssh-key` without known-hosts content/path or an explicit unknown-host-acceptance opt-in
- **THEN** composition or startup fails with an error naming the missing host-key configuration, rather than allowing an unverified connection at ingestion time

### Requirement: Basic ingestion upsert
Given a registered repository containing a valid `catalog-info.yaml`, ingestion SHALL create or update every entity in the file to match, and re-ingesting the same file SHALL update the same entity rather than creating a duplicate. Every such create or update SHALL be performed through the core Entity Service via an `EntityIntent`, not by writing catalog models directly.

#### Scenario: First ingestion creates entities
- **WHEN** the ingestor runs against a repository with a valid manifest for the first time
- **THEN** every entity in the file exists in the catalog with fields matching the file, marked YAML-managed

#### Scenario: Re-ingestion updates in place
- **WHEN** a `catalog-info.yaml` is edited and pushed, and the ingestor next runs
- **THEN** the corresponding entity's fields are updated to match, without creating a duplicate entity

#### Scenario: Upsert is indistinguishable from a manual write at the Entity Service boundary
- **WHEN** ingestion creates or updates an entity
- **THEN** the same common-metadata validation and audit recording that a manual API write would trigger also runs for the ingestion write

### Requirement: Per-manifest failure isolation
A manifest document that fails schema validation SHALL be skipped and logged for that run, without rolling back other entities ingested from the same run.

#### Scenario: One invalid document doesn't block the rest
- **WHEN** a manifest with an invalid `kind` or a missing required `spec` field is processed in the same run as other valid documents
- **THEN** the invalid document is skipped and logged, and the other valid documents in the same run still ingest successfully

### Requirement: Multi-document manifests
A single `catalog-info.yaml` SHALL support multiple `---`-separated documents, each ingested as a separate entity.

#### Scenario: One file declares a System and its Components
- **WHEN** a manifest contains three `---`-separated documents (one System, two Components)
- **THEN** all three entities are created or updated from that single file

### Requirement: YAML manifests declare architecture relationships in entity specs
The ingestion pipeline SHALL accept outgoing `spec.relationships` declarations for supported catalog entities, validate their fields and target refs, and reconcile them as YAML-origin Architecture Relationships after entity upsert and reference resolution.

#### Scenario: Manifest declares an API call
- **WHEN** a Component manifest declares a relationship to another Component with label `Makes API calls to`, technology `REST/HTTPS`, and kind `synchronous`
- **THEN** ingestion creates or updates the matching YAML-origin Architecture Relationship

#### Scenario: Reference order within a manifest does not matter
- **WHEN** a manifest declares an Architecture Relationship whose target is defined later in the same multi-document file
- **THEN** ingestion resolves the target after entity upsert and creates the relationship

#### Scenario: Re-ingestion removes a deleted declaration
- **WHEN** a YAML-managed source entity is re-ingested without one of its prior `spec.relationships` declarations
- **THEN** the corresponding YAML-origin Architecture Relationship is removed while manual relationships remain unchanged

#### Scenario: Unresolved declared target is isolated as a manifest error
- **WHEN** a manifest declares an Architecture Relationship to an unknown target ref
- **THEN** the invalid declaration is reported and no partial YAML-origin relationship is created for it

### Requirement: Ingestion reconciles whole-entity disappearance (fixes the zombie-entity bug)
When a `RegisteredRepository`'s re-ingested manifests no longer declare an entity that repository previously claimed (`source_kind=yaml`, same claiming repository), that entity's `CatalogEntity` SHALL become `removed` in the same ingestion pass that already prunes its YAML-origin relationships — the entity SHALL NOT be left `active` indefinitely. This SHALL run through the Entity Service the same way any other ingestion write does, and SHALL apply symmetrically to how `ApiEndpoint`/`ApiOperation` disappearance is already reconciled.

#### Scenario: An entity dropped from a manifest becomes removed, not a zombie
- **WHEN** a repo's `catalog-info.yaml` is re-ingested without a Component it previously declared
- **THEN** that Component's status becomes `removed` in the same pass, alongside the existing pruning of its YAML-origin relationships — it no longer remains `active` with silently-missing edges

#### Scenario: A removed-by-ingestion entity keeps its id and prior relations for history
- **WHEN** ingestion removes an entity because its manifest declaration disappeared
- **THEN** the entity's row, kind-details, and its non-pruned relations remain in the database, unlike a hard delete

### Requirement: Auto-remove authority is sticky to the entity's own origin
An ingestion source SHALL only be able to auto-remove an entity that it itself claims (`source_kind=yaml` with that same `RegisteredRepository`); it SHALL NEVER auto-remove a manually-created entity, nor an entity claimed by a different repository. An ingestion run that no longer sees a ref it does not claim SHALL NOT affect that ref's entity at all.

#### Scenario: Ingestion cannot remove a manually-created entity
- **WHEN** a manually-created Component happens to share a ref that a repository's manifest no longer declares (and never claimed)
- **THEN** ingestion reconciliation does not change that Component's status, since the repository never claimed it

#### Scenario: One repository's reconciliation does not affect another repository's claim
- **WHEN** Repository R1's manifest no longer declares a ref, but that ref is actually claimed by Repository R2
- **THEN** R1's ingestion run does not remove or otherwise change the entity claimed by R2

### Requirement: An entity removed by ingestion revives automatically when re-declared
When a `RegisteredRepository` re-declares a ref that its own previously-claimed entity currently holds in `removed` status, that entity SHALL become `active` again (Revive), with its fields updated from the manifest per the existing same-repo re-claim overwrite rule, and its id and non-pruned relations unchanged.

#### Scenario: Re-adding a dropped declaration revives the entity
- **WHEN** Repository R1 previously stopped declaring Component `checkout` (causing it to become `removed`) and later re-declares it
- **THEN** `checkout`'s status becomes `active` again, its fields are overwritten in full from the manifest, and its id is unchanged from before it was removed

### Requirement: YAML ingestion fully reconciles described metadata links
Ingestion SHALL accept an optional `description` on each `metadata.links[]`
entry in `catalog-info.yaml`. On every successful upsert it SHALL replace the
YAML-managed entity's complete metadata-link list, including descriptions,
with the manifest declaration.

#### Scenario: Ingestion stores a described dashboard link
- **WHEN** a System manifest declares a link with a title, description, URL,
  and type
- **THEN** the retrieved System and its document-links API expose those four
  values

#### Scenario: Removed YAML link disappears after re-ingestion
- **WHEN** a YAML-managed System is re-ingested with one previously declared
  metadata link removed
- **THEN** that link is absent from the System's subsequent document-links API
  response

#### Scenario: YAML-managed links cannot be manually changed
- **WHEN** a user attempts to PATCH `metadata.links` on a YAML-managed System
- **THEN** the request is rejected and the manifest-derived links remain
  unchanged

### Requirement: Fetched content is bounded before parsing
Any content fetched by a connector on behalf of the ingestion pipeline — a discovered manifest, an `Include`-resolved fragment, or a `sourceSqlPath`-resolved file — SHALL be subject to a configured maximum byte size, and any YAML parsed from that content SHALL be subject to a configured maximum document size and nesting depth. Content exceeding either limit SHALL be rejected and reported as a failed resolution for that path, without blocking ingestion of the rest of the repository's manifests.

#### Scenario: An oversized fetched file is rejected before parsing
- **WHEN** a connector fetches a file whose size exceeds the configured maximum fetched-file size
- **THEN** the file is rejected and reported as a failed resolution, and it is not passed to the YAML parser

#### Scenario: Excessively nested YAML is rejected
- **WHEN** a fetched manifest or fragment parses as YAML whose nesting depth exceeds the configured maximum
- **THEN** the document is rejected and reported as a failed resolution, and ingestion of the rest of the repository's manifests proceeds unaffected

### Requirement: Manifest-processing failures are persisted and admin-visible
In addition to being logged, a manifest-processing failure that is already isolated per repository-relative path (connector fetch failure, YAML parse failure, manifest schema-validation failure, and a failed or unresolved `Include` per the `ingestion-manifest-includes` capability) SHALL be recorded as an `IngestionIssue`, keyed by `(repository, path)`, viewable through Django admin without access to application logs. Recording an `IngestionIssue` SHALL NOT change the existing per-manifest failure isolation behavior: the failing path is still skipped and the rest of that run still proceeds.

#### Scenario: A fetch failure is recorded and visible in admin
- **WHEN** a registered repository's connector fails to fetch a discovered `catalog-info.yaml` path during a run
- **THEN** that failure is logged as before, and an `IngestionIssue` for that repository and path is visible in Django admin

#### Scenario: A parse failure is recorded and visible in admin
- **WHEN** a discovered manifest file's content fails to parse as YAML
- **THEN** that failure is logged as before, and an `IngestionIssue` for that repository and path is visible in Django admin

#### Scenario: A schema-validation failure is recorded and visible in admin
- **WHEN** a manifest document fails entity-kind schema validation (the existing "One invalid document doesn't block the rest" scenario)
- **THEN** that failure is logged as before, and an `IngestionIssue` for that repository and path is visible in Django admin

### Requirement: An IngestionIssue is self-clearing
An `IngestionIssue` for a given `(repository, path)` SHALL be marked inactive once that same repository and path complete a subsequent ingestion run without the failure that created it, mirroring the existing self-clearing behavior of `ConflictRecord`.

#### Scenario: A fixed manifest clears its prior issue
- **WHEN** a `catalog-info.yaml` that previously failed schema validation is corrected and the repository is re-ingested successfully
- **THEN** the corresponding `IngestionIssue` becomes inactive without being deleted

#### Scenario: A recurring failure updates the existing issue rather than duplicating it
- **WHEN** the same repository and path fail ingestion in the same way across multiple consecutive runs
- **THEN** a single `IngestionIssue` row for that `(repository, path)` has its message and last-seen time updated, rather than a new row being created per run
