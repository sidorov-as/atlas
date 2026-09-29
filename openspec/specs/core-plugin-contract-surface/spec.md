# core-plugin-contract-surface Specification

## Purpose
Core publishes the plugin-facing surface it actually expects plugins to use — a base entity type, Entity Kind registration, entity read/write access, and auth/permission registration — through versioned types in `atlas_plugin_api`/`@atlas/plugin-api`, instead of plugins reaching into `server.apps.catalog`/`server.apps.plugins` internals directly. This makes a plugin's declared `compatibility.atlasCore` range a real, enforceable promise rather than a decorative one: Core's semver carries an obligation to keep the published contract surface stable, and CI rejects any plugin import of a Core internal that isn't part of that surface.

## Requirements

### Requirement: Core publishes its plugin-facing surface as contract types
Core SHALL expose every part of its plugin-facing surface that first-party plugins actually rely on — a base entity type, Entity Kind registration, entity read/write access, and auth/permission registration — through versioned types in `atlas_plugin_api`/`@atlas/plugin-api`, rather than requiring plugins to import `server.apps.catalog`/`server.apps.plugins` modules directly.

#### Scenario: A plugin references the published base entity type
- **WHEN** a plugin's Django model or application code refers to the catalog entity type (as an FK/`OneToOneField` target, a type hint, or an ORM query)
- **THEN** it imports the base entity type published by `atlas_plugin_api`, not `server.apps.catalog.models.base.CatalogEntity` directly

#### Scenario: A plugin registers an Entity Kind through the published registry accessor
- **WHEN** a plugin registers a new Entity Kind handler
- **THEN** it does so through a registration function/protocol published by `atlas_plugin_api`, not by importing `server.apps.catalog.kinds.registry` directly

#### Scenario: A plugin reads or writes entities through the published service protocol
- **WHEN** a plugin needs to read or write catalog entities from application code (not Django ORM model definitions)
- **THEN** it does so through an entity-service protocol published by `atlas_plugin_api`, not `server.apps.catalog.services.entity_service` directly

#### Scenario: A plugin registers a permission through the published registration protocol
- **WHEN** a plugin declares a permission id it checks
- **THEN** it registers that id through an auth/permission registration protocol published by `atlas_plugin_api`/`@atlas/plugin-api`, not `server.apps.plugins.permissions`/`server.apps.catalog.authorization` directly

### Requirement: Plugin imports of unpublished Core internals fail CI
The import-boundary check SHALL reject a plugin importing a `server.apps.catalog`/`server.apps.plugins` module that isn't part of the published `atlas_plugin_api`/`@atlas/plugin-api` contract surface.

#### Scenario: An unpublished Core internal import fails the boundary check
- **WHEN** a plugin's package imports a `server.apps.catalog`/`server.apps.plugins` module not re-exported by `atlas_plugin_api`
- **THEN** the import-boundary check fails, identifying the forbidden import

#### Scenario: A published contract type import passes the boundary check
- **WHEN** a plugin's package imports a type from `atlas_plugin_api`/`@atlas/plugin-api`
- **THEN** the import-boundary check passes, regardless of what Core internal that type wraps

### Requirement: Core publishes authentication provider collaboration contracts
Core SHALL publish provider descriptors, credential and redirect flow protocols, normalized source-bound identity, attribute-provenance, group-snapshot, and failure types, provider registration, provisioning collaboration services, presentation metadata, and contract-test helpers through `atlas_plugin_api`. Authentication plugins SHALL NOT need Core-internal models, registries, settings modules, allauth adapters, or session functions.

#### Scenario: Plugin registers an authentication provider
- **WHEN** a third-party plugin activates its runtime entry point
- **THEN** it registers its provider through `atlas_plugin_api.register_authentication_provider` or the versioned equivalent

#### Scenario: Plugin returns a verified identity
- **WHEN** provider verification succeeds
- **THEN** it constructs the public normalized identity type and Core consumes it without the plugin importing Django User, ExternalIdentityLink, Actor, or Group implementation models

#### Scenario: Plugin imports Core auth internals
- **WHEN** an authentication plugin imports `server.apps.catalog.authentication`, Core settings, provisioning models, or an unpublished registry
- **THEN** the import-boundary check fails and points to the public authentication contract

### Requirement: Static and runtime authentication contributions are separated
The published contract SHALL distinguish static contributions needed during composition/settings generation from runtime provider registration performed after Django setup. Plugin authors SHALL be able to declare Django apps, config schemas, provider ids, flow metadata, and optional route modules without import-time ORM access.

#### Scenario: Provider descriptor is inspected before Django setup
- **WHEN** the composer or settings generator loads a provider plugin descriptor
- **THEN** the descriptor can be validated without importing Django models or executing provider runtime code

#### Scenario: Runtime provider uses ORM-independent public services
- **WHEN** Django setup completes and the provider registers
- **THEN** Core binds the public provisioning/session collaboration services needed after verification
