# policy-evaluator-extension Specification

## Purpose
The Authorization Service delegates every permission check to exactly one selected `PolicyEvaluator`, so that authorization logic (including plugin-declared permissions) is centralized behind a single pluggable decision point instead of scattered kind-specific view logic or parallel role systems.

## Requirements

### Requirement: Authorization decisions are delegated to one selected policy evaluator
The Authorization Service SHALL delegate ordinary permission decisions to exactly one selected PolicyEvaluator singleton resolved from deployment configuration, subject to mandatory Core account restrictions evaluated before delegation. Core and public Plugin API evaluator access SHALL expose the guarded service, not an unguarded selected implementation. A selected evaluator SHALL NOT override a Core read-only denial.

#### Scenario: A permission check calls the selected evaluator
- **WHEN** backend code checks a permission that is not denied by a mandatory Core restriction
- **THEN** the selected evaluator produces the ordinary permission decision

#### Scenario: Alternate evaluator would permit a read-only write
- **WHEN** a read-only Principal requests a write while a custom selected evaluator would return true
- **THEN** Core denies it before invoking the evaluator's allow branch

### Requirement: Plugins declare permissions, never a parallel role system
A plugin SHALL declare its permission ids in its own namespace and request decisions from the Authorization Service; it SHALL NOT implement its own independent role or authorization mechanism.

#### Scenario: A plugin-declared permission is evaluated by the shared evaluator
- **WHEN** a plugin checks its own namespaced permission (e.g. `atlas.c4.diagram.read`)
- **THEN** the check is evaluated by the deployment's single selected `PolicyEvaluator`, the same one used for core permissions

### Requirement: Built-in RBAC evaluator reproduces existing ownership rules
The built-in RBAC evaluator SHALL grant edit permission on a manual entity to members of its owning Group and to superusers only when no mandatory Core account restriction denies the write. It SHALL grant read permission on any entity to any authenticated Principal, including read-only Principals. Group membership and stored Purge Grants SHALL retain their existing meaning independently of AccountAccess.

#### Scenario: Owner-Group member can edit
- **WHEN** a non-read-only member of Group G requests edit permission on a manual entity owned by G
- **THEN** the built-in RBAC evaluator grants it

#### Scenario: Non-member cannot edit
- **WHEN** a non-superuser who is not a member of an entity's owning Group requests edit permission
- **THEN** the built-in RBAC evaluator denies it

#### Scenario: Read-only membership stays intact
- **WHEN** a read-only Group member requests a write
- **THEN** the write is denied without deleting or falsifying that Principal's membership

### Requirement: Core enforces the read-only override before write privileges
Core SHALL deny read-only writes before superuser, ownership, Purge Grant or selected-evaluator shortcuts. Independent mutation paths, including resource-less entity creation, direct privilege guards, admin and job dispatch, SHALL invoke the same shared restriction before applying ordinary authorization. No change to PolicyEvaluator.check arguments SHALL be required for this guard.

#### Scenario: Read-only account creates an owned entity
- **WHEN** creation has no resource yet and the Principal belongs to the intended owner Group
- **THEN** the shared guard denies the read-only Principal before membership can authorize creation

#### Scenario: Read-only superuser requests purge
- **WHEN** a read-only superuser or Purge Grant holder requests purge
- **THEN** the restriction denies it before evaluating those privileges

### Requirement: Permission effects are explicit and fail closed
Permission registration SHALL support effect read or write. Existing registered ids ending in .read SHALL default to read; all other registered ids SHALL default to write. An explicit read declaration SHALL identify a side-effect-free user operation and have conformance coverage. Invalid or conflicting effect declarations SHALL fail registration/composition. Unknown or unregistered permissions SHALL be denied for read-only callers regardless of evaluator behavior. Existing normal-account permission semantics SHALL not otherwise change.

#### Scenario: Plugin uses a nonstandard write suffix
- **WHEN** a plugin registers a .sync or .execute permission without explicit read effect and a read-only Principal requests it
- **THEN** Core classifies it as write and denies it

#### Scenario: Unknown permission reaches a permissive evaluator
- **WHEN** a read-only Principal requests an unregistered permission
- **THEN** Core denies it before a superuser shortcut or permissive evaluator can allow it

#### Scenario: Nonstandard read operation is declared
- **WHEN** a plugin explicitly registers a side-effect-free query permission as read
- **THEN** read-only callers can obtain ordinary evaluator decisions for it without being granted extra read privileges

### Requirement: Plugin mutation checks use the guarded public service
Plugins SHALL use the Core-guarded public authorization surface for user mutations and SHALL NOT obtain an unguarded evaluator, rely only on is_superuser, or claim service identity from caller-controlled input. Conformance tests SHALL cover permission effect declarations and rejection before side effects. The SDK SHALL document that installed server plugins are trusted code and these contracts do not sandbox malicious implementations.

#### Scenario: Plugin mutation is called directly
- **WHEN** a read-only Principal bypasses the UI and invokes a plugin write operation
- **THEN** the guarded public service denies it before data changes or job enqueueing
