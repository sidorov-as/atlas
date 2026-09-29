## ADDED Requirements

### Requirement: Built-in provider outbound requests resist DNS rebinding
Built-in redirect-flow providers (OIDC, Gitea) that validate the resolved
address of an outbound request before making it SHALL connect using that
same validated address, not a second, independent resolution of the
hostname. The original hostname SHALL still be used for the `Host` header
and TLS SNI, so certificate validation and hostname-based routing on the
issuer/instance side are unaffected.

#### Scenario: DNS answer changes between validation and connection
- **WHEN** a configured issuer or instance hostname resolves to an allowed
  address at validation time and a different, prohibited address a moment
  later
- **THEN** the provider's outbound request connects to the validated
  address, not the later one, and TLS/Host behavior for the original
  hostname is unaffected

#### Scenario: Hostname resolves to an allowed address consistently
- **WHEN** a configured issuer or instance hostname resolves to the same
  allowed address at validation and connection time
- **THEN** the request succeeds exactly as it did before this requirement
  was introduced
