## ADDED Requirements

### Requirement: CatalogEntity gains a Removed status, decoupled from deprecated
Every CatalogEntity of kind System, Component, Resource, or API SHALL carry a `status` of `active` or `removed`, independent of any `deprecated`/`lifecycle` cosmetic flag. `removed` SHALL NOT be a mandatory waypoint reachable only after `deprecated`, and SHALL NOT delete the entity's row, kind-details row, or any existing relation/link that referenced it.

#### Scenario: An entity can become removed without ever being deprecated
- **WHEN** an active, never-deprecated Component is removed
- **THEN** its status becomes `removed` and its row, kind-details, and existing relations remain in the database unchanged

#### Scenario: A deprecated entity is not automatically removed
- **WHEN** an entity is marked `deprecated`
- **THEN** its `status` remains `active` until a separate, explicit Remove action or ingestion reconciliation changes it

### Requirement: Removed applies at the container level; children are removed implicitly
`Removed` SHALL apply to System, Component, Resource, and API entities (and, per the `api-endpoints`/`api-operations` capabilities, to their `ApiEndpoint`/`ApiOperation` children). No independent `removed` lifecycle SHALL exist for any other sub-resource. When a container entity is removed, its children SHALL be treated as removed for all display and reference-checking purposes without requiring their own `status` to be individually set.

#### Scenario: Removing an API implicitly removes its endpoints for display purposes
- **WHEN** an `api` entity with active Endpoints is removed
- **THEN** views of that API's endpoints reflect the API's removed status without requiring each Endpoint's own `status` to change

### Requirement: Manual Remove is an explicit, human/API-triggered action
A manually-created (`source_kind=manual`) entity SHALL become `removed` only via an explicit Remove action invoked by a permitted user or API caller — never via automatic staleness detection, since a manual entity has no external source of truth to diff against.

#### Scenario: A manual entity is removed by an explicit action
- **WHEN** a permitted user invokes Remove on a manually-created, currently-active Component
- **THEN** the Component's status becomes `removed`, and this happened only because of that explicit action, not any automatic process

#### Scenario: A manual entity is never auto-removed
- **WHEN** time passes with no explicit Remove action invoked on a manually-created entity
- **THEN** its status remains `active` indefinitely, regardless of how stale its data may be

### Requirement: Revive restores a Removed entity to active, preserving identity
Reviving a `removed` entity SHALL set its status back to `active` while preserving its existing `id`, relations, and audit history — it SHALL NOT create a new entity or new id. Revive SHALL happen automatically when the same origin that created the entity re-declares the same ref (see `catalog-ingestion`); for a manually-removed entity, an explicit human-triggered Revive action SHALL also be available, since no automatic re-declaration is possible for it.

#### Scenario: Manual revive of a manually-removed entity
- **WHEN** a permitted user invokes Revive on a manually-removed Component
- **THEN** the Component's status becomes `active` again, with its original id, relations, and audit history intact

#### Scenario: Revive never changes the entity's id
- **WHEN** any removed entity is revived, by any path
- **THEN** its `id` after revival is identical to its `id` before removal

#### Scenario: A YAML-managed removed entity cannot be manually revived
- **WHEN** a user invokes a manual Revive action on a `removed` entity with `source_kind=yaml`
- **THEN** the request is rejected regardless of the user's Group membership; that entity can only become `active` again through ingestion reconciliation re-declaring its ref (see `catalog-ingestion`)

### Requirement: Purge is a new, explicit action reachable only from Removed
`Purge` SHALL be a destructive action available only on an entity whose current status is `removed` — never directly from `active`. Purging an entity SHALL permanently delete its `CatalogEntity` row and kind-details row, and SHALL be the only action that frees its `(kind, namespace, name)` slot for reuse by a genuinely new entity with a new id; no purged entity's history, relations, or id SHALL be inherited by whatever new entity later claims that name.

#### Scenario: Purge is rejected on an active entity
- **WHEN** Purge is invoked on an entity whose status is `active`
- **THEN** the request is rejected — the entity must be removed first

#### Scenario: Purge frees the name for a genuinely new entity
- **WHEN** a `removed` Component named `checkout` is purged, and a new entity is later created with the same name
- **THEN** the new entity is created with a new id, and no data, relation, or history from the purged entity is associated with it

#### Scenario: Purge applies uniformly regardless of prior reference history
- **WHEN** an entity that never had any incoming reference is removed and then purged
- **THEN** the purge succeeds via the same remove-then-purge path as any other entity, with no direct active-to-purge shortcut having been available

### Requirement: Purge validation scans both FK-backed and ref-string-backed references
Before a `removed` entity may be purged, the system SHALL check for any reference to it that is still `active`, including FK-backed relations (`dependsOn`, `providesApis`, `consumesApis`, `owner`) and ref-string-backed references resolved dynamically at read time (e.g. Flow steps' `entity_ref`, `query_ref`, `event_ref`). Purge SHALL be blocked, with a named list of blocking references, if any such active reference exists. Purge SHALL be permitted to proceed, cascading the removal of the reference records themselves, if every remaining reference to the entity is itself in a removed/non-active state.

#### Scenario: Purge blocked by an active FK-backed reference
- **WHEN** Purge is invoked on a `removed` Component that another, active Component's `dependsOn` still references
- **THEN** the purge is rejected with a named list including the referencing Component

#### Scenario: Purge blocked by an active ref-string-backed reference
- **WHEN** Purge is invoked on a `removed` entity that an active Flow step's `entity_ref` still references
- **THEN** the purge is rejected with a named list including that Flow

#### Scenario: Purge succeeds when all references are already removed
- **WHEN** Purge is invoked on a `removed` entity whose only remaining references are themselves removed (a removed relationship row, or a removed referencing entity)
- **THEN** the purge succeeds, and those removed-status reference rows are cleaned up as part of the same operation

#### Scenario: Purge succeeds trivially when nothing ever referenced the entity
- **WHEN** Purge is invoked on a `removed` entity that has zero references, active or removed
- **THEN** the purge succeeds immediately

### Requirement: Purge Grant permission is scoped per owner-Group, with a global-admin override
Purge SHALL require a `Purge Grant`: either membership in a set of users a given owner-Group's own admins have elevated to hold Purge rights for entities owned by that Group, or global-admin status. A Purge Grant SHALL authorize Purge on a `removed` entity regardless of that entity's `source_kind` (manual or yaml) — this is a deliberate, narrow carve-out from the otherwise-uniform rule that YAML-managed entities reject all manual writes.

#### Scenario: Group-scoped grant holder purges an entity owned by their group
- **WHEN** a user holding a Purge Grant scoped to Group *G* invokes Purge on a `removed` entity owned by *G*
- **THEN** the purge is authorized and proceeds (subject to the reference-scanning check)

#### Scenario: Grant does not cross group boundaries
- **WHEN** a user holding a Purge Grant scoped to Group *G* invokes Purge on a `removed` entity owned by a different Group *H*
- **THEN** the request is rejected, unless that user is also a global admin

#### Scenario: Global admin purges regardless of grant or source_kind
- **WHEN** a global admin invokes Purge on any `removed` entity, including one with `source_kind=yaml`
- **THEN** the purge is authorized and proceeds (subject to the reference-scanning check), without requiring a group-scoped grant

#### Scenario: A YAML-managed entity is purgeable by a grant holder despite the general manual-write block
- **WHEN** a user holding a Purge Grant for the owning Group invokes Purge on a `removed`, `source_kind=yaml` entity
- **THEN** the purge is authorized, even though that same user could not manually edit or delete that entity while it was active

### Requirement: Remove/Revive/Purge are audited and visible on a History tab
Every Remove, Revive, and Purge action SHALL be recorded through the same Entity Service transactional audit mechanism used for create/update/delete, and the entity detail page SHALL expose a minimal, read-only History section listing these events (who/what performed the action, and when).

#### Scenario: Removing an entity produces an audit record
- **WHEN** an entity is removed, whether by explicit action or ingestion reconciliation
- **THEN** an audit record is created identifying the action, its actor (or the ingestion process), and the timestamp

#### Scenario: History tab shows past lifecycle events
- **WHEN** a user opens the History section of an entity that has been removed and later revived
- **THEN** both the removal and the revival appear, each with their actor and timestamp

### Requirement: Removed entities are hidden from default views with an ungated toggle
List and search views for CatalogEntity kinds SHALL exclude `removed` entities by default, and SHALL offer an explicit "show removed" toggle available to any authenticated catalog viewer — visibility of removed entities SHALL NOT be restricted to the owning Group or to any other subset of users.

#### Scenario: Removed entity is absent from the default list
- **WHEN** a user views a Components list with no "show removed" toggle applied
- **THEN** `removed` Components are not shown

#### Scenario: Any viewer can reveal removed entities
- **WHEN** a user who is not a member of the removed entity's owner Group and not a superuser enables "show removed"
- **THEN** removed entities owned by any Group become visible to them, since removed status is not sensitive
