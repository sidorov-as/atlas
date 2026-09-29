## ADDED Requirements

### Requirement: Composition rejects identity and version mismatches
The composer SHALL reject a manifest whose full-stack plugin has mismatched backend/frontend plugin identities or versions, or whose Core or Plugin API compatibility ranges are not satisfied.

#### Scenario: Mismatched backend and frontend versions are rejected
- **WHEN** a manifest selects a backend artifact version and a frontend artifact version for the same logical plugin that don't match
- **THEN** the composer rejects the build, identifying the mismatch

### Requirement: Composition rejects missing dependencies and cycles
The composer SHALL reject a manifest missing a required plugin, capability, or extension point that a selected plugin depends on, and SHALL reject a cyclic plugin dependency graph.

#### Scenario: A missing required dependency fails the build
- **WHEN** a selected plugin declares a required manifest dependency that isn't itself selected
- **THEN** the composer rejects the build, naming the missing dependency

#### Scenario: A dependency cycle fails the build
- **WHEN** selected plugins' manifest dependencies form a cycle
- **THEN** the composer rejects the build, identifying the cycle

### Requirement: Composition rejects duplicate ids and path conflicts
The composer SHALL reject a manifest whose selected plugins together declare a duplicate Entity Kind, Facet, permission, contribution, capability, or route id, or a conflicting or core-reserved route path.

#### Scenario: Duplicate contribution id across two plugins fails the build
- **WHEN** two selected plugins each declare a contribution with the same id
- **THEN** the composer rejects the build, identifying both conflicting plugins and the shared id

### Requirement: Composition rejects invalid configuration and forbidden dependency edges
The composer SHALL reject a manifest with invalid non-secret plugin configuration, and SHALL reject a build whose resolved package dependency graph contains a forbidden edge (a plugin importing another plugin's implementation, or importing core internals).

#### Scenario: Invalid plugin configuration fails the build
- **WHEN** a selected plugin's non-secret configuration in the manifest doesn't validate against its declared schema
- **THEN** the composer rejects the build, identifying the invalid configuration field

#### Scenario: A forbidden import edge fails CI
- **WHEN** a plugin's package imports another plugin's implementation module rather than a declared contract package
- **THEN** the import-boundary check fails, identifying the forbidden import
