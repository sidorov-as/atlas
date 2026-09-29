## ADDED Requirements

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
