# entity-claim-arbitration Specification

## Purpose
Governs how an entity ref first gets assigned a `source_kind` (`manual` or `yaml`), how first-claim collisions between a manual entity and a YAML claim (or between two competing repos) are arbitrated and recorded, and how a manual entity can be explicitly adopted into YAML control.

## Requirements

### Requirement: Entity source tracking
Every ingestible entity (System, Component, Resource, API) SHALL record a `source_kind` of `manual` or `yaml`, and, when `yaml`, the `RegisteredRepository` that claims it.

#### Scenario: Manual creation sets source_kind
- **WHEN** a user creates a System, Component, Resource, or API via the web UI or API
- **THEN** the entity is stored with `source_kind=manual` and no claiming repository

#### Scenario: Ingestion sets source_kind
- **WHEN** the ingestor upserts an entity from a `catalog-info.yaml`
- **THEN** the entity is stored with `source_kind=yaml` and the claiming `RegisteredRepository` set

### Requirement: First-claim arbitration
When an ingestion run encounters a ref, the system SHALL arbitrate against any existing entity's source rather than silently overwriting it. Arbitration SHALL happen before an `EntityIntent` is submitted to the core Entity Service; a rejected claim SHALL NOT reach the Entity Service at all.

#### Scenario: YAML claims an unclaimed ref
- **WHEN** ingestion encounters a ref with no existing entity
- **THEN** a new entity is created with `source_kind=yaml` and the claiming repository set

#### Scenario: YAML collides with a manual entity
- **WHEN** ingestion encounters a ref already claimed by a manual entity
- **THEN** the ingestion claim is rejected before any `EntityIntent` is submitted, a conflict is recorded, and the manual entity's fields are unchanged

#### Scenario: Same repo re-claims its own entity
- **WHEN** ingestion encounters a ref already claimed by the same `RegisteredRepository`
- **THEN** the entity's fields are overwritten in full from the manifest, via an `EntityIntent` submitted to the Entity Service

#### Scenario: A different repo collides with an existing YAML claim
- **WHEN** ingestion encounters a ref already claimed by a different `RegisteredRepository`
- **THEN** the ingestion claim is rejected before any `EntityIntent` is submitted, a conflict is recorded, and the existing entity's fields are unchanged

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

### Requirement: A Removed entity's claim still blocks a rival
A ref claimed by an entity currently in `removed` status SHALL continue to block a rival claim on that ref, the same as an `active` entity's claim does; the rival claim SHALL be rejected with a specific `removed_entity` ConflictRecord reason, distinguishing it from the existing `manual_entity`/`other_repository` reasons.

#### Scenario: A different repo cannot claim a name held by a removed entity
- **WHEN** Repository R2 attempts to declare a ref that Repository R1's now-`removed` entity still holds
- **THEN** the claim is rejected, a `removed_entity`-reason ConflictRecord is written naming R1 and the removed entity, and no `EntityIntent` is submitted

#### Scenario: Removed-entity conflict banner names the blocking repository
- **WHEN** a user views the conflict banner produced by a `removed_entity` conflict
- **THEN** the banner names the repository whose removed entity is blocking the claim, and states that an owner must revive or purge it before the new claim can succeed

#### Scenario: A manual claim is also blocked by a removed manual entity
- **WHEN** a user attempts to manually create an entity with a ref already held by a `removed` manual entity of the same kind/namespace/name
- **THEN** the creation is rejected with a `removed_entity`-reason conflict, the same as attempting to create over an active manual entity would be

#### Scenario: The blocking claim clears once the removed entity is purged
- **WHEN** a `removed` entity blocking a rival claim is purged
- **THEN** the next ingestion run (or manual creation attempt) for that ref succeeds, without any cache-invalidation step being required, per the existing no-cached-arbitration rule

### Requirement: Repository unregistration is blocked while claimed
A `RegisteredRepository` SHALL NOT be deletable/unregistered while any entity has `source_kind=yaml` with its repository FK pointing at it, regardless of whether that entity's status is `active` or `removed`. Cascade-delete of claimed entities and orphan-and-keep (clearing `source_kind`) are not supported; the block is cleared by purging each claimed entity individually — removing it first if it is still active, then purging it with a valid Purge Grant, per the `entity-removal-lifecycle` capability. This resolves the previous gap where the manual-write block on YAML-managed entities left no path to actually clear claimed entities ahead of unregistration.

#### Scenario: Unregistration rejected while entities are claimed
- **WHEN** an operator attempts to delete a `RegisteredRepository` that at least one entity still claims via `source_kind=yaml`, whether `active` or `removed`
- **THEN** the deletion is rejected and no entity or repository state changes

#### Scenario: Unregistration succeeds once every claimed entity is purged
- **WHEN** every entity that claims a `RegisteredRepository` has been removed (if still active) and then purged by a Purge Grant holder, and the operator then attempts to delete the repository
- **THEN** the repository is deleted successfully

### Requirement: Conflict records survive repository deletion
Every conflict record SHALL store the claiming repository's full name as a snapshot at write time, independent of its live repository FK, so historical conflict records remain meaningful and do not block repository deletion.

#### Scenario: Historical conflicts don't block deletion
- **WHEN** a `RegisteredRepository` has only historical (non-active) conflict records and no entity currently claims it
- **THEN** the repository can be deleted, and its past conflict records still display the repository's name via the snapshot field
