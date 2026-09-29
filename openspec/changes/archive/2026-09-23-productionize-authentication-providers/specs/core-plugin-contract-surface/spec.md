## ADDED Requirements

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

