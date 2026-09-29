## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Repository unregistration is blocked while claimed
A `RegisteredRepository` SHALL NOT be deletable/unregistered while any entity has `source_kind=yaml` with its repository FK pointing at it, regardless of whether that entity's status is `active` or `removed`. Cascade-delete of claimed entities and orphan-and-keep (clearing `source_kind`) are not supported; the block is cleared by purging each claimed entity individually — removing it first if it is still active, then purging it with a valid Purge Grant, per the `entity-removal-lifecycle` capability. This resolves the previous gap where the manual-write block on YAML-managed entities left no path to actually clear claimed entities ahead of unregistration.

#### Scenario: Unregistration rejected while entities are claimed
- **WHEN** an operator attempts to delete a `RegisteredRepository` that at least one entity still claims via `source_kind=yaml`, whether `active` or `removed`
- **THEN** the deletion is rejected and no entity or repository state changes

#### Scenario: Unregistration succeeds once every claimed entity is purged
- **WHEN** every entity that claims a `RegisteredRepository` has been removed (if still active) and then purged by a Purge Grant holder, and the operator then attempts to delete the repository
- **THEN** the repository is deleted successfully
