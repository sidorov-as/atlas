## MODIFIED Requirements

### Requirement: Composer resolves the manifest to a lock file
The composer SHALL resolve a manifest to a lock file recording the exact backend and frontend artifact package and version for every selected plugin and Core. The lock file SHALL NOT record artifact integrity hashes; integrity of installed artifacts is established by the native Python and npm lock files and the installers that verify them.

#### Scenario: Lock file records exact versions
- **WHEN** the composer resolves a manifest
- **THEN** the resulting lock file records, for every selected plugin, its exact backend and frontend artifact packages and versions

#### Scenario: Lock file carries no integrity hashes
- **WHEN** the composer resolves a manifest
- **THEN** no plugin entry in the resulting lock file contains a `hash` or `integrity` value

#### Scenario: Declared version disagrees with the native lock
- **WHEN** a manifest declares a plugin version that differs from the version recorded for its package in the native lock file
- **THEN** resolution fails identifying the plugin, the declared version and the native lock's version

#### Scenario: Lock with legacy integrity fields is loaded
- **WHEN** the composer loads a lock file whose plugin entries still carry `hash` or `integrity` fields
- **THEN** loading fails and instructs the operator to re-resolve the lock from the manifest

## ADDED Requirements

### Requirement: Resolution is stable under unrelated source edits
Resolving an unchanged manifest against unchanged native lock files SHALL produce a byte-identical lock file, regardless of edits to plugin source files.

#### Scenario: Plugin source is edited
- **WHEN** a source file inside a workspace plugin changes and the manifest and native lock files do not
- **THEN** re-resolving produces a lock file identical to the previously committed one

#### Scenario: Committed lock is stale
- **WHEN** a manifest or native lock changes without the distribution's lock file being re-resolved
- **THEN** re-resolving produces a lock file that differs from the committed one, and the repository's continuous-integration check fails
