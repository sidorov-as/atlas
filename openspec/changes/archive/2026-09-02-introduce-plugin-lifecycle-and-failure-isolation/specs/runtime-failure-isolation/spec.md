## ADDED Requirements

### Requirement: Every contribution is isolated by an error boundary
Every frontend contribution (route, tab, action, banner, home widget) SHALL be wrapped in an error boundary such that its failure does not crash the application shell or any other contribution.

#### Scenario: A failing home widget does not crash the home page
- **WHEN** a home widget contribution throws during render
- **THEN** the home page continues to render its other widgets and shell chrome, showing a visible failed state only for the broken widget

### Requirement: Capability calls return a typed unavailable or error result
A cross-plugin capability call SHALL return a typed result distinguishing success, unavailable (the providing plugin isn't installed or active), and error, rather than raising or returning an ambiguous empty value.

#### Scenario: Calling a capability with no provider returns Unavailable
- **WHEN** code calls a capability whose providing plugin is not installed
- **THEN** the call returns a typed Unavailable result, distinguishable from a successful call that returned no data

### Requirement: A plugin endpoint failure does not affect unrelated requests
An internal failure in one plugin-owned endpoint SHALL return a clean degraded response and SHALL NOT affect requests to other plugins' or core's endpoints.

#### Scenario: One plugin's endpoint failing does not break another plugin's endpoint
- **WHEN** a plugin-owned endpoint fails internally
- **THEN** it returns a clean error response, and a concurrent request to a different plugin's or core's endpoint succeeds normally

### Requirement: Health diagnostics surface per-plugin degraded status
A health/diagnostics endpoint SHALL report each installed plugin's status, distinguishing healthy from degraded.

#### Scenario: A degraded plugin is visible in health diagnostics
- **WHEN** a plugin is in a degraded state
- **THEN** the health/diagnostics endpoint reports that plugin as degraded, distinct from healthy plugins
