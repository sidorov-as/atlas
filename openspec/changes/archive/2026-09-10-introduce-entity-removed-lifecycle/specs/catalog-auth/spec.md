## ADDED Requirements

### Requirement: Purge Grant permission, scoped per owner-Group with a global-admin override
Purging a `removed` entity SHALL require a `Purge Grant`: a permission a Group's own admins can assign to specific members, scoped to entities owned by that Group, or global-admin status which authorizes Purge on any entity regardless of grant or `source_kind`. This permission SHALL be enforced by the built-in RBAC `PolicyEvaluator`, the same mechanism enforcing ownership-based edit permission, not by kind-specific view logic.

#### Scenario: Owner-Group admin grants Purge rights to a member
- **WHEN** an admin of Group *G* assigns a Purge Grant scoped to *G* to a member of *G*
- **THEN** that member can subsequently invoke Purge on any `removed` entity owned by *G*

#### Scenario: Purge Grant does not authorize edits or remove/revive
- **WHEN** a user holding only a Purge Grant (and not owner-Group membership) attempts to edit, remove, or revive an active or removed entity owned by that Group
- **THEN** the edit/remove/revive request is rejected — Purge Grant authorizes Purge specifically, not the full set of write actions

#### Scenario: Global admin needs no Purge Grant
- **WHEN** a global admin invokes Purge on a `removed` entity owned by a Group they have no grant for
- **THEN** the purge is authorized

### Requirement: Removing an owning Group or Actor is blocked while it still owns active entities
A Group or Actor that still owns one or more `active` System, Component, Resource, or API SHALL NOT be deletable; `owner` SHALL be treated as a protected reference, checked the same way any other dependency is checked before a delete is allowed. An owner that only owns `removed` entities MAY be deleted.

#### Scenario: Deleting a Group with active owned entities is blocked
- **WHEN** an operator attempts to delete a Group that is the `owner` of at least one `active` Component
- **THEN** the deletion is rejected, naming the active entities still owned by that Group

#### Scenario: Deleting a Group whose owned entities are all removed succeeds
- **WHEN** every entity a Group owns has status `removed`, and an operator attempts to delete that Group
- **THEN** the deletion succeeds

#### Scenario: No entity is left displaying a nonexistent owner
- **WHEN** an owner-deletion attempt is blocked by this rule
- **THEN** no active entity is left referencing a Group or Actor that no longer exists

## MODIFIED Requirements

### Requirement: Ownership-based edit permission
A user SHALL be able to edit, remove, or revive a manual entity only if they are a member of that entity's `owner` Group, or a superuser; this rule SHALL apply uniformly across every Entity Kind and SHALL be enforced by the built-in RBAC `PolicyEvaluator`, not by kind-specific view logic. Purge SHALL instead require a Purge Grant (or global-admin status), not merely owner-Group membership.

#### Scenario: Owner-Group member can edit any registered kind
- **WHEN** a member of Group *G* attempts to edit a manual entity of any registered kind owned by *G*
- **THEN** the request succeeds and the fields are updated

#### Scenario: Superuser can edit regardless of Group membership
- **WHEN** a superuser attempts to edit a manual entity owned by a Group they are not a member of
- **THEN** the request succeeds

#### Scenario: Owner-Group member can remove and revive a manual entity
- **WHEN** a member of Group *G* invokes Remove, and later Revive, on a manual entity owned by *G*
- **THEN** both actions succeed under the same ownership-based permission that governs editing

#### Scenario: Owner-Group membership alone does not authorize Purge
- **WHEN** a member of Group *G* who holds no Purge Grant attempts to Purge a `removed` entity owned by *G*
- **THEN** the request is rejected — owner-Group membership authorizes edit/remove/revive, but Purge requires its own grant
