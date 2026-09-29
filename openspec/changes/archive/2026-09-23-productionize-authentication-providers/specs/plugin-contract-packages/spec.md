## ADDED Requirements

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

