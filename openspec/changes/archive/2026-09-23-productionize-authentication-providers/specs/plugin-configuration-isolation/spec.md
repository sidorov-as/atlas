## ADDED Requirements

### Requirement: Authentication providers receive typed namespaced configuration
Every authentication provider SHALL declare a typed configuration schema owned by its provider plugin or Core component. Provider code SHALL receive only its validated resolved configuration and SHALL NOT read arbitrary global Django settings or environment variables directly.

#### Scenario: Custom LDAP provider starts
- **WHEN** the selected LDAP plugin is activated
- **THEN** it receives only its validated LDAP configuration object and centrally resolved secret values

#### Scenario: Provider configuration contains an unknown field
- **WHEN** a manifest supplies a provider config field absent from its schema
- **THEN** composition fails before deployment startup

### Requirement: Authentication secrets never enter public or persistent artifacts
Client secrets, bind passwords, submitted credentials, access tokens, refresh tokens, ID tokens, and equivalent provider secrets SHALL NOT appear in manifests as literal production values, locks, generated modules, frontend bundles, public bootstrap responses, health output, exception responses, or logs.

#### Scenario: OIDC client secret resolves
- **WHEN** the OIDC provider resolves its client secret from an environment reference
- **THEN** only the backend provider instance receives the value in memory

#### Scenario: Provider exception includes upstream body
- **WHEN** an upstream identity service returns a body containing token or credential material
- **THEN** Atlas sanitizes it before logging or returning an error

### Requirement: Provider public projection contains presentation data only
The frontend authentication bootstrap SHALL expose only selected provider id, display name, flow kind, default status, safe credential-field presentation metadata, signup availability, and other explicitly public behavior needed to render login. Issuers, discovery internals, directory addresses, client ids unless explicitly required, client secrets, bind identities, mapping expressions, and raw claims SHALL remain backend-only.

#### Scenario: Login page reads provider config
- **WHEN** the frontend loads authentication bootstrap configuration
- **THEN** it can render selected providers and default behavior without receiving connection or secret configuration

### Requirement: Secret-bearing authentication configuration is redacted consistently
All configuration inspection, validation errors, diagnostics, repr/serialization helpers, and test snapshots SHALL use one central redaction policy for secret-capable provider fields.

#### Scenario: Provider config validation fails beside a secret
- **WHEN** a non-secret field is invalid in a config object that also contains a resolved secret
- **THEN** the error identifies the invalid field without serializing the secret-bearing object


### Requirement: Authentication outbound requests have a controlled trust boundary
Production authentication connections SHALL verify TLS certificates and hostnames, use bounded connection/read/overall deadlines and response sizes, and never downgrade to plaintext after a TLS failure. Core/provider configuration SHALL declare allowed identity-service destinations; metadata-discovered token, UserInfo, JWKS, logout, and redirect targets SHALL be validated against that policy. Arbitrary caller-supplied URLs, cloud metadata destinations, and automatic credential forwarding to a new origin SHALL be rejected. Private identity-service destinations SHALL require explicit configuration; validation SHALL account for redirects and resolved addresses. Deliberate plaintext development fixtures SHALL require a development-only opt-in that production configuration rejects.

#### Scenario: Discovery advertises an unexpected endpoint
- **WHEN** trusted discovery returns a token or JWKS endpoint outside the configured destinations
- **THEN** Atlas rejects it without sending secrets or making the prohibited request

#### Scenario: Certificate verification fails
- **WHEN** an identity service presents an invalid certificate or hostname
- **THEN** verification fails and no insecure retry is performed

### Requirement: Provider token retention and observability are explicit
Provider tokens and raw credential/protocol payloads SHALL be transient by default and SHALL not be stored by framework token-saving features, database records, signed-cookie sessions, browser storage, tracing, or request-body capture. Optional remote logout that requires token retention SHALL declare a bounded server-side protected retention policy with deletion on logout/expiry; tokens SHALL never appear in URLs except a protocol-required logout parameter sent only to the validated provider endpoint. Application and example proxy/access logs SHALL redact callback query parameters and sensitive request bodies. Errors and diagnostics SHALL use allowlisted safe fields rather than rely solely on matching secret values.

#### Scenario: Callback passes through access logging
- **WHEN** a callback contains an authorization code and state in its query
- **THEN** captured application, proxy, test, and diagnostic logs contain neither value

#### Scenario: Remote logout is not configured
- **WHEN** an OAuth/OIDC login completes
- **THEN** upstream tokens are discarded after verification instead of being retained by the underlying library
