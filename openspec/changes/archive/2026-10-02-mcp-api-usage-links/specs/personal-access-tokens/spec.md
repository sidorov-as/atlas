## ADDED Requirements

### Requirement: apis:write is an issuable scope
Atlas SHALL accept `apis:write` as a Personal Access Token scope wherever scopes are chosen or validated: the token issuance paths and the admin form. It SHALL be offered together with the existing scopes, SHALL be listed with a human-readable label, and SHALL only permit what the owning user's RBAC already permits.

#### Scenario: Issuing a token with apis:write
- **WHEN** a token is issued with the scopes `catalog:read` and `apis:write`
- **THEN** it is issued and its scopes contain both

#### Scenario: Unknown scope is still rejected
- **WHEN** a token is issued with a scope that Atlas does not define
- **THEN** issuance is rejected

#### Scenario: apis:write does not broaden RBAC
- **WHEN** a token with `apis:write` belongs to a user who cannot link a Service to an Endpoint interactively
- **THEN** the same link attempted with the token is denied
