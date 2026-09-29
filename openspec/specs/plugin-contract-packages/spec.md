# plugin-contract-packages Specification

## Purpose
A plugin that other first-party plugins legitimately need to depend on — starting with `atlas_plugin_standard_catalog`, the de facto hub other plugins build on — publishes a declared contract-only package or submodule covering exactly the surface other plugins need, instead of those plugins importing its Django models, schemas, or other implementation modules directly. This lets a depended-on plugin's implementation evolve independently of its dependents, and makes the plugin-to-plugin boundary enforceable by CI rather than documented as an allowlisted exception.

## Requirements

### Requirement: A depended-on plugin publishes a declared contract-only package
A plugin that other first-party plugins legitimately need to depend on SHALL publish a declared contract-only package or submodule — types and value objects only, no Django models or business logic — covering exactly the surface other plugins need, instead of those plugins importing its implementation modules directly.

#### Scenario: A dependent plugin imports the contract package instead of implementation
- **WHEN** one plugin needs a type or value defined by another plugin (e.g. an ingestion pipeline referencing a standard-catalog entity type)
- **THEN** it imports that type from the depended-on plugin's declared contract-only package, not from the depended-on plugin's Django models or other implementation modules

#### Scenario: A contract-only package contains no implementation
- **WHEN** a plugin's contract-only package/submodule is inspected
- **THEN** it contains only type/value definitions (e.g. Pydantic schemas, protocols, dataclasses), with no Django model classes, database queries, or business logic

### Requirement: Plugin-to-plugin implementation imports fail CI
The import-boundary check SHALL reject a plugin importing another plugin's implementation module rather than that plugin's declared contract-only package.

#### Scenario: A direct implementation import fails the boundary check
- **WHEN** a plugin's package imports another plugin's Django model, view, or other implementation module directly
- **THEN** the import-boundary check fails, identifying the forbidden import and naming the contract package that should be used instead

#### Scenario: A contract-package import passes the boundary check
- **WHEN** a plugin's package imports from another plugin's declared contract-only package
- **THEN** the import-boundary check passes

### Requirement: Authentication provider contracts are versioned package surface
The Python Plugin API SHALL export `atlas.auth.providers.v1` contract types and registration functions as a documented semver-governed surface. Any matching TypeScript types used by login presentation SHALL be exported from `@atlas/plugin-api` or an explicitly Core-owned bootstrap contract; neither package SHALL expose provider implementation internals.

#### Scenario: Provider plugin declares compatibility
- **WHEN** a plugin built against authentication provider contract v1 is selected
- **THEN** the composer validates its Atlas Core and Plugin API compatibility before activation

#### Scenario: Contract changes incompatibly
- **WHEN** a future release removes or incompatibly changes a required v1 provider contract
- **THEN** the responsible package/Core version changes according to the documented compatibility policy and incompatible plugins fail composition

### Requirement: Authentication contract packages remain implementation-free
The provider contract modules SHALL contain protocols, dataclasses/value objects, enums, configuration base types, exceptions, and testing helpers only. They SHALL NOT query Atlas models, establish sessions, perform network authentication, or depend on provider-specific libraries.

#### Scenario: Contract module is imported by composer
- **WHEN** composition imports provider descriptor and schema types outside a running Django application
- **THEN** import succeeds without database access, network access, or Django application initialization

### Requirement: Contract tests are consumable outside the monorepo
The authentication provider contract-test kit SHALL be installable and runnable by a separately packaged third-party plugin. Tests SHALL accept provider fixtures/factories through documented hooks and SHALL not depend on repository-private test fixtures.

#### Scenario: custom credential example consumes contract tests
- **WHEN** the separately packaged custom credential example runs its tests
- **THEN** it imports the published test kit and supplies only documented provider-specific fixtures
