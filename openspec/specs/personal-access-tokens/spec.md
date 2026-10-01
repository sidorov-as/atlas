## Purpose

Personal Access Tokens are Atlas's credential for non-interactive, tool-calling clients (currently `atlas.mcp`) to authenticate as a real Django user without a session. A token carries scopes that narrow — never broaden — its owning user's own RBAC, so an operation it authenticates is permitted only when both the token's scopes and the underlying user's RBAC allow it. Validation checks the token's own hash, expiry, and revocation state, and independently the owning account's active status, so a deactivated account's token stops working even though the token's own fields say nothing changed.

## Requirements

### Requirement: A user can issue a Personal Access Token
A user SHALL be able to issue an Atlas Personal Access Token for themselves. The plaintext token value SHALL be shown exactly once, at issuance time; Atlas SHALL persist only a salted hash and a short lookup prefix, never the plaintext.

#### Scenario: Issuing a token displays plaintext exactly once
- **WHEN** a user issues a new Personal Access Token
- **THEN** the plaintext value is displayed once in that response, and no later request (including by that same user) can retrieve it again

#### Scenario: Stored token data never contains plaintext
- **WHEN** a Personal Access Token record is inspected in the database
- **THEN** it contains only a hash and a short lookup prefix, never the plaintext value

### Requirement: A token's scopes narrow, never broaden, its owner's RBAC
A Personal Access Token SHALL carry one or more scopes (e.g. `catalog:read`, `catalog:write`, `flows:write`). At authorization time, an operation SHALL be permitted only if it is both allowed by the token's scopes and allowed by its owning user's own RBAC — a token SHALL NOT grant an operation its owning user could not otherwise perform.

#### Scenario: A token cannot exceed its owner's own RBAC
- **WHEN** a Personal Access Token's scopes would permit an operation, but the token's owning user's RBAC would deny that same operation if performed interactively
- **THEN** the operation is denied

### Requirement: A token supports expiry and revocation
A Personal Access Token SHALL support an `expires_at` and a `revoked_at`, either of which its owner can set. Validation SHALL reject a token whose `expires_at` has passed or whose `revoked_at` is set.

#### Scenario: Expired token is rejected
- **WHEN** a request presents a token whose `expires_at` is in the past
- **THEN** the request is rejected

#### Scenario: Revoked token is rejected immediately
- **WHEN** a user revokes a token, and a subsequent request presents that same token
- **THEN** the request is rejected

### Requirement: Token validation also depends on the owning account's active status
Validation SHALL reject a Personal Access Token whose owning user account is not active, independent of the token's own `expires_at`/`revoked_at` values.

#### Scenario: Token belonging to a deactivated account is rejected
- **WHEN** a request presents a Personal Access Token whose owning user account has been deactivated, and the token itself is neither expired nor revoked
- **THEN** the request is rejected

### Requirement: Token usage is tracked
A Personal Access Token's `last_used_at` SHALL be updated whenever it is used to authenticate a request successfully.

#### Scenario: Successful authentication updates last_used_at
- **WHEN** a valid, non-expired, non-revoked token authenticates a request
- **THEN** that token's `last_used_at` reflects the time of that request
