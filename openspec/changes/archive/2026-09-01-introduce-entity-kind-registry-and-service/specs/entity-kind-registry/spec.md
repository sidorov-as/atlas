## ADDED Requirements

### Requirement: Kind handlers register against a stable kind id
An Entity Kind provider SHALL register exactly one `EntityKindHandler` per `kind_id`, exposing a `spec_schema` and `create_details`/`update_details`/`serialize_details`/`validate_delete` operations.

#### Scenario: Registering a kind handler
- **WHEN** a provider registers a handler for `kind_id="system"`
- **THEN** the registry accepts it and subsequent lookups for `"system"` return that handler

### Requirement: Duplicate kind registration is rejected
The registry SHALL reject a second handler registering an already-registered `kind_id`.

#### Scenario: Two handlers claim the same kind id
- **WHEN** a second provider attempts to register a handler for `kind_id="system"` while one is already registered
- **THEN** registration fails with an error identifying the conflicting `kind_id`

### Requirement: Unknown kind is a uniform lookup failure
Resolving a `kind_id` with no registered handler SHALL return a distinguishable "unknown kind" result rather than raising an unhandled exception or silently matching an unrelated handler.

#### Scenario: Looking up an unregistered kind
- **WHEN** the registry is asked for a handler for a `kind_id` with no registered provider
- **THEN** it returns a typed "not found" result that callers can handle explicitly
