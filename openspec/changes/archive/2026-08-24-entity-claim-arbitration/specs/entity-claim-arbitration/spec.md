## ADDED Requirements

### Requirement: Entity source tracking
Every ingestible entity (System, Component, Resource, API) SHALL record a `source_kind` of `manual` or `yaml`, and, when `yaml`, the `RegisteredRepository` that claims it.

#### Scenario: Manual creation sets source_kind
- **WHEN** a user creates a System, Component, Resource, or API via the web UI or API
- **THEN** the entity is stored with `source_kind=manual` and no claiming repository

#### Scenario: Ingestion sets source_kind
- **WHEN** the ingestor upserts an entity from a `catalog-info.yaml`
- **THEN** the entity is stored with `source_kind=yaml` and the claiming `RegisteredRepository` set

### Requirement: First-claim arbitration
When an ingestion run encounters a ref, the system SHALL arbitrate against any existing entity's source rather than silently overwriting it.

#### Scenario: YAML claims an unclaimed ref
- **WHEN** ingestion encounters a ref with no existing entity
- **THEN** a new entity is created with `source_kind=yaml` and the claiming repository set

#### Scenario: YAML collides with a manual entity
- **WHEN** ingestion encounters a ref already claimed by a manual entity
- **THEN** the ingestion claim is rejected, a conflict is recorded, and the manual entity's fields are unchanged

#### Scenario: Same repo re-claims its own entity
- **WHEN** ingestion encounters a ref already claimed by the same `RegisteredRepository`
- **THEN** the entity's fields are overwritten in full from the manifest

#### Scenario: A different repo collides with an existing YAML claim
- **WHEN** ingestion encounters a ref already claimed by a different `RegisteredRepository`
- **THEN** the ingestion claim is rejected, a conflict is recorded, and the existing entity's fields are unchanged

### Requirement: No cached arbitration
Every ingestion run SHALL re-evaluate arbitration from current state, without short-circuiting on a previous run's result.

#### Scenario: Deleting the blocking entity unblocks the rival claim
- **WHEN** a manual entity that previously blocked a YAML claim is deleted, and the ingestor runs again
- **THEN** the YAML claim is created successfully on this run, without any cache-invalidation step being required

### Requirement: Conflict visibility
A rejected claim SHALL produce a persisted conflict record and a visible signal on the blocked entity.

#### Scenario: Conflict record created
- **WHEN** an ingestion claim is rejected due to arbitration
- **THEN** a conflict record is created or updated with the repository, ref, reason, and first/last-seen timestamps, visible in Django admin

#### Scenario: Blocked entity shows a banner
- **WHEN** a user views the detail page of an entity that is currently blocking a YAML claim
- **THEN** the page shows a banner naming the repository that could not claim it

### Requirement: Intra-repo duplicate rejection
A single ingestion run SHALL reject two manifests in the same repo that declare the same ref, rather than resolving them by upsert order.

#### Scenario: Duplicate ref within one run
- **WHEN** a single ingestion run's manifests declare the same `(kind, namespace, name)` more than once
- **THEN** neither declaration is upserted for that ref, and the duplicate is logged

### Requirement: One-directional adoption
A manual entity SHALL be adoptable into YAML control by a permitted user; a YAML-managed entity SHALL never be adoptable back to manual.

#### Scenario: Owner adopts a manual entity
- **WHEN** a member of the entity's owner Group (or a superuser) calls `POST /api/{kind}/{id}/adopt/` naming a registered repository
- **THEN** the entity's `source_kind` is set to `yaml` and the claiming repository is set, without its other fields changing immediately

#### Scenario: Non-owner cannot adopt
- **WHEN** a user who is not a member of the entity's owner Group and not a superuser calls the adopt endpoint
- **THEN** the request is rejected with 403 and the entity's `source_kind` is unchanged

#### Scenario: Adopted entity is overwritten on next ingestion
- **WHEN** a manual entity has been adopted by a repository and the ingestor next runs a manifest for the same ref from that repository
- **THEN** the entity's fields are overwritten in full, per the same-repo re-claim rule

#### Scenario: No reverse adoption
- **WHEN** any user attempts to change a YAML-managed entity's `source_kind` to `manual`
- **THEN** the request is rejected regardless of permissions

### Requirement: Repository unregistration is blocked while claimed
A `RegisteredRepository` SHALL NOT be deletable/unregistered while any entity has `source_kind=yaml` with its repository FK pointing at it. Cascade-delete of claimed entities and orphan-and-keep (clearing `source_kind`) are not supported; the only way to clear the block is deleting each claimed entity individually.

#### Scenario: Unregistration rejected while entities are claimed
- **WHEN** an operator attempts to delete a `RegisteredRepository` that at least one entity still claims via `source_kind=yaml`
- **THEN** the deletion is rejected and no entity or repository state changes

#### Scenario: Unregistration succeeds once nothing claims the repository
- **WHEN** an operator deletes every entity that claims a `RegisteredRepository`, then attempts to delete the repository
- **THEN** the repository is deleted successfully

### Requirement: Conflict records survive repository deletion
Every conflict record SHALL store the claiming repository's full name as a snapshot at write time, independent of its live repository FK, so historical conflict records remain meaningful and do not block repository deletion.

#### Scenario: Historical conflicts don't block deletion
- **WHEN** a `RegisteredRepository` has only historical (non-active) conflict records and no entity currently claims it
- **THEN** the repository can be deleted, and its past conflict records still display the repository's name via the snapshot field
