## MODIFIED Requirements

### Requirement: Secrets are resolved centrally and never exposed
A configuration value referencing a secret SHALL be resolved by a central configuration service; the resolved secret value SHALL NOT appear in the manifest, the lock file, the frontend bundle, or any public bootstrap response. Resolution SHALL apply recursively to secret references nested inside list or sub-model configuration fields, not only to top-level fields.

#### Scenario: A secret reference resolves without leaking
- **WHEN** a plugin's configuration declares a secret via an environment reference
- **THEN** the plugin receives the resolved value at runtime, and no build artifact, lock file, or frontend-visible response contains that value

#### Scenario: A secret reference nested in a list resolves
- **WHEN** a plugin's configuration declares a list field whose items each contain a secret reference
- **THEN** every item's secret reference is resolved, and the plugin receives each item with its resolved value, not the unresolved reference

## ADDED Requirements

### Requirement: File-based secret references
A configuration field that may hold a secret SHALL be able to reference a file on disk (`{fromFile: <path>}`) as an alternative to an environment variable reference (`{fromEnv: <var>}`), for secret material such as private keys that does not fit cleanly into a single-line environment variable. A field SHALL resolve from exactly one reference kind at a time.

#### Scenario: A file-based secret reference resolves
- **WHEN** a plugin's configuration declares a secret via a file reference pointing at a mounted, readable file
- **THEN** the plugin receives that file's contents as the resolved value at runtime, and no build artifact, lock file, or frontend-visible response contains it

#### Scenario: A missing referenced file fails startup
- **WHEN** a plugin's configuration declares a file reference whose path does not exist or is not readable
- **THEN** configuration resolution fails with an error naming the field and the missing path, before the plugin receives any configuration
