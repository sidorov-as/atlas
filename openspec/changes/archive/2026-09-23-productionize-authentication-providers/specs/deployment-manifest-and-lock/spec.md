## ADDED Requirements

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
