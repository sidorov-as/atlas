## ADDED Requirements

### Requirement: Contributions are declared, not registered imperatively
A frontend plugin module SHALL export an immutable list of contributions via `defineFrontendPlugin`. It SHALL NOT mutate a global registry as a module-import side effect.

#### Scenario: Importing a plugin module has no side effect
- **WHEN** a plugin module is imported
- **THEN** no route, tab, or nav item becomes active as a result of the import alone; only passing its exported definition into the host's composition step activates its contributions

### Requirement: Contribution ids are globally unique
Every route, nav item, entity-detail tab, and home widget contribution SHALL have a globally unique id; composition SHALL fail when two contributions share an id.

#### Scenario: Duplicate contribution id fails composition
- **WHEN** two contributions declare the same id
- **THEN** the host's composition step fails before the router is constructed, identifying both conflicting contributions

### Requirement: Route paths do not conflict
Two route contributions SHALL NOT declare the same path, and no plugin route SHALL use a core-reserved path.

#### Scenario: Conflicting route paths fail composition
- **WHEN** two route contributions declare the same `path`
- **THEN** composition fails, identifying both conflicting routes

#### Scenario: A core-reserved path is rejected
- **WHEN** a route contribution declares a path reserved by core
- **THEN** composition fails, identifying the reserved path

### Requirement: Route references resolve before composition completes
A `routeRef` used by a nav item or cross-plugin link SHALL resolve to a declared route id; an unresolved reference SHALL fail composition with an identifying error.

#### Scenario: Nav item references an undeclared route
- **WHEN** a nav item's `routeRef` names a route id that no contribution declares
- **THEN** composition fails, identifying the unresolved reference

### Requirement: Composition is validated before the router is built
The full set of installed plugins' contributions SHALL be validated (ids, paths, route references, extension-point cardinality) before the router or application shell is constructed.

#### Scenario: A validation failure prevents the app from rendering the broken state
- **WHEN** composition validation fails
- **THEN** the application does not render a partially-built router; it surfaces the composition error instead
