## ADDED Requirements

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
