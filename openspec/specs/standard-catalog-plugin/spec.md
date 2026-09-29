## Purpose

Standard Catalog is the plugin that supplies Atlas's baseline Entity Kinds — System, Component, Resource, Team, and Actor. Atlas Core itself registers no concrete Entity Kind; every Kind is provided by a plugin, and Standard Catalog is the official distribution's required plugin for the standard set. This keeps identity, storage, and lifecycle plumbing in Core generic while Kind-specific behavior (including Team's admin-only creation and Actor's identity role) lives in the plugin.

## Requirements

### Requirement: Core has no concrete Entity Kinds
Atlas Core SHALL register no Entity Kind itself; System, Component, Resource, Team, and Actor SHALL be provided entirely by the Standard Catalog plugin.

#### Scenario: Core builds and starts with Standard Catalog deselected
- **WHEN** a distribution is composed without `atlas.standard-catalog` selected (for a boundary test, not for normal operation)
- **THEN** core still starts successfully, registering zero Entity Kinds itself

### Requirement: Standard Catalog is required in the official distribution
The official Atlas distribution SHALL fail composition if `atlas.standard-catalog` is not selected.

#### Scenario: Omitting the required plugin fails composition
- **WHEN** a deployment selection omits `atlas.standard-catalog`
- **THEN** composition validation fails, naming the missing required plugin

### Requirement: Team is a registered Entity Kind
Team (backed by `Group`) SHALL be a registered Entity Kind with its own `EntityKindHandler`, on equal footing with System, Component, and Resource for identity, storage, and lifecycle plumbing, without changing the existing restriction that Teams are creatable only through Django admin, not the public REST API (`entity-catalog`'s "Group and User are read-only via API").

#### Scenario: Django admin creation goes through the Entity Service
- **WHEN** an administrator creates a Team via Django admin
- **THEN** it is created through the same Entity Service pipeline as System, Component, and Resource, using Team's registered kind handler

#### Scenario: Public REST creation remains rejected
- **WHEN** a request attempts `POST /api/groups/`
- **THEN** the request is still rejected, unchanged from the existing `entity-catalog` requirement

### Requirement: Actor is a registered Entity Kind
Actor (renamed from `User`) SHALL be a registered Entity Kind with its own `EntityKindHandler`, providing the identity that Architecture Relationships and Group membership reference, without gaining a public list/detail page or REST create path beyond what the current PoC's `User` model has today.

#### Scenario: Actor identity is used by Group membership and relationships
- **WHEN** an Actor is referenced by `Group.members` or as an Architecture Relationship endpoint
- **THEN** the reference resolves via the Actor's `CatalogEntity.id`, the same mechanism used for every other kind

#### Scenario: Actor has no public creation path
- **WHEN** a request attempts to create an Actor via the public REST API
- **THEN** the request is rejected, matching the current PoC's admin-managed-only `User` behavior
