## ADDED Requirements

### Requirement: Authorization decisions are delegated to one selected policy evaluator
The Authorization Service SHALL delegate every permission check to exactly one selected `PolicyEvaluator` singleton, resolved from the deployment's configuration.

#### Scenario: A permission check calls the selected evaluator
- **WHEN** backend code checks whether a principal has a given permission on a resource
- **THEN** the decision is produced by the currently selected `PolicyEvaluator`, not by inline per-view logic

### Requirement: Plugins declare permissions, never a parallel role system
A plugin SHALL declare its permission ids in its own namespace and request decisions from the Authorization Service; it SHALL NOT implement its own independent role or authorization mechanism.

#### Scenario: A plugin-declared permission is evaluated by the shared evaluator
- **WHEN** a plugin checks its own namespaced permission (e.g. `atlas.c4.diagram.read`)
- **THEN** the check is evaluated by the deployment's single selected `PolicyEvaluator`, the same one used for core permissions

### Requirement: Built-in RBAC evaluator reproduces existing ownership rules
The built-in RBAC evaluator SHALL grant edit permission on a manual entity to members of its owning Group and to superusers, and SHALL grant read permission on any entity to any authenticated principal.

#### Scenario: Owner-Group member can edit
- **WHEN** a member of Group *G* requests an edit permission check on a manual entity owned by *G*
- **THEN** the built-in RBAC evaluator grants it

#### Scenario: Non-member cannot edit
- **WHEN** a user who is not a member of an entity's owning Group and not a superuser requests an edit permission check on that entity
- **THEN** the built-in RBAC evaluator denies it
