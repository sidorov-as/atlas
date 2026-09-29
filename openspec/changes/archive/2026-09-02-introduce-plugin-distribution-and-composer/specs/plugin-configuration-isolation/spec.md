## ADDED Requirements

### Requirement: A plugin receives only its own namespaced configuration
A plugin SHALL receive only its own validated, namespaced configuration object; it SHALL NOT read global Django settings or environment variables directly.

#### Scenario: A plugin cannot see another plugin's configuration
- **WHEN** a plugin's code runs
- **THEN** it can access only its own declared configuration object, not any other plugin's

### Requirement: Secrets are resolved centrally and never exposed
A configuration value referencing a secret SHALL be resolved by a central configuration service; the resolved secret value SHALL NOT appear in the manifest, the lock file, the frontend bundle, or any public bootstrap response.

#### Scenario: A secret reference resolves without leaking
- **WHEN** a plugin's configuration declares a secret via an environment reference
- **THEN** the plugin receives the resolved value at runtime, and no build artifact, lock file, or frontend-visible response contains that value

### Requirement: Frontend receives only an explicitly declared public projection
A plugin's frontend code SHALL receive only the configuration fields its backend explicitly declares as a public projection; no other configuration field SHALL be exposed to the frontend.

#### Scenario: An undeclared config field is not sent to the frontend
- **WHEN** a plugin's backend configuration includes a field not declared in its public projection
- **THEN** that field is absent from the bootstrap configuration response sent to the frontend
