# deployment-manifest-and-lock Specification

## Purpose
The source-controlled deployment manifest and composer-generated lock file through which an operator declares plugin selection and the composer resolves that selection into a reproducible build — replacing ad hoc, hand-edited plugin lists with a manifest+lock pair that fully determines a deployment's composition and requires no network access at container start.

## Requirements

### Requirement: Manifest declares plugin selection and artifact sources
An operator SHALL declare selected plugins, their versions, and their backend/frontend artifact sources in a source-controlled deployment manifest.

#### Scenario: Manifest names an explicit plugin and version
- **WHEN** an operator adds an entry to the manifest naming a plugin id, version, and artifact sources
- **THEN** the composer resolves that exact plugin and version for the build

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

### Requirement: Nothing is downloaded at container start
A built container image SHALL contain every artifact its lock file specifies; starting the container SHALL NOT fetch any plugin artifact over the network.

#### Scenario: Container starts without network access
- **WHEN** a built container starts with no outbound network access
- **THEN** it starts successfully using only artifacts already present in the image

### Requirement: A build is reproducible from manifest and lock alone
Given the same manifest and lock file, the composer SHALL produce a build with the same selected plugin versions and generated composition.

#### Scenario: Rebuilding from the same lock produces the same composition
- **WHEN** the composer runs twice against the same manifest and lock file
- **THEN** both runs select the same plugin versions and generate the same `INSTALLED_APPS` and frontend plugin list

### Requirement: Manifest declares authoritative authentication selection
The deployment manifest SHALL declare a non-empty ordered set of authentication provider ids and exactly one selected default. The composer SHALL validate provider existence, uniqueness, compatibility, required artifacts, flow metadata, and that the default is selected.

#### Scenario: Valid authentication selection composes
- **WHEN** a manifest selects compatible registered providers and names one of them as default
- **THEN** composition succeeds and preserves their order and default in generated runtime configuration

#### Scenario: Manifest omits authentication selection
- **WHEN** a manifest using the new schema omits providers or default
- **THEN** composition fails with migration guidance rather than silently enabling local authentication

#### Scenario: Provider implementation is missing
- **WHEN** auth selection names a provider whose owning artifact is absent
- **THEN** composition fails identifying the provider and required plugin/artifact

### Requirement: Lock records authentication behavior without resolved secrets
The lock SHALL record selected provider ids, default provider, flow-compatible public metadata, provisioning modes, group reconciliation modes, and the unresolved secret-reference structure needed for reproducibility. It SHALL NOT contain resolved client secrets, passwords, bind credentials, tokens, or other secret values.

#### Scenario: Authentication lock is regenerated
- **WHEN** the same manifest and provider artifacts are resolved twice
- **THEN** both locks contain the same auth selection and non-secret policy values

#### Scenario: Secret reference is used
- **WHEN** provider configuration refers to an environment secret
- **THEN** the lock preserves only the reference metadata permitted by the config contract and never the resolved value

### Requirement: Composer generates authentication runtime inputs
The composer SHALL generate backend and frontend inputs sufficient to enforce provider selection, default behavior, flow presentation, signup policy, provisioning policy, and group reconciliation without hand-editing Django settings or frontend source.

#### Scenario: OIDC-only distribution is generated
- **WHEN** the manifest selects only OIDC
- **THEN** generated backend settings enable the selected provider and block local login/signup while generated frontend inputs omit the local form

#### Scenario: Custom provider is selected
- **WHEN** the manifest selects a compatible third-party provider plugin
- **THEN** its declared Django apps/static requirements and provider metadata are included through normal composition rather than deployment-specific source edits

### Requirement: Authentication manifest migration is explicit
The schema transition that makes auth selection authoritative SHALL provide validation and migration guidance for existing manifests. The checked-in official distribution SHALL explicitly select its intended providers, default, signup policy, and provisioning policy.

#### Scenario: Legacy manifest is validated
- **WHEN** an existing manifest with defaulted empty auth fields is validated against the new composer
- **THEN** validation reports the exact auth block required to preserve the previous local-only behavior

### Requirement: Security policies are explicit generated deployment inputs
The manifest and lock SHALL represent identity source bindings, restricted-attribute assurance requirements, explicit group mappings, finite session maximum age, finite exact-group freshness, public origin and outbound trust policy, local password/recovery policy, and admin-password recovery mode/allowlist. Session and exact-group ages SHALL default to eight hours and SHALL not permit unlimited or non-positive values. Admin password login SHALL default to disabled. Provider configuration SHALL not expose these backend-only controls through the public login projection. Security-related configuration changes SHALL apply to existing sessions and grants, not only future logins.

#### Scenario: Operator changes an identity authority
- **WHEN** configuration replaces a provider source that has existing links
- **THEN** runtime source binding validation requires a reviewed migration or new namespace and never silently reuses old links

#### Scenario: Invalid lifetime or break-glass policy is composed
- **WHEN** a manifest supplies an unlimited lifetime or enables admin password recovery without an explicit Principal allowlist
- **THEN** composition fails with a safe actionable diagnostic

### Requirement: Resolution is stable under unrelated source edits
Resolving an unchanged manifest against unchanged native lock files SHALL produce a byte-identical lock file, regardless of edits to plugin source files.

#### Scenario: Plugin source is edited
- **WHEN** a source file inside a workspace plugin changes and the manifest and native lock files do not
- **THEN** re-resolving produces a lock file identical to the previously committed one

#### Scenario: Committed lock is stale
- **WHEN** a manifest or native lock changes without the distribution's lock file being re-resolved
- **THEN** re-resolving produces a lock file that differs from the committed one, and the repository's continuous-integration check fails
