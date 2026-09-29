## ADDED Requirements

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
