## ADDED Requirements

### Requirement: Revoking or expiring a token invalidates the upload tickets it issued
When a Personal Access Token is revoked or has expired, every unused upload ticket it issued SHALL stop being accepted. Deactivating the owning account SHALL have the same effect.

#### Scenario: Revoked token's tickets stop working
- **WHEN** a token that issued an unused upload ticket is revoked
- **THEN** a later upload to that ticket is rejected

#### Scenario: Other tokens' tickets are unaffected
- **WHEN** one token is revoked
- **THEN** unused tickets issued by a different token remain valid until their own expiry
