## ADDED Requirements

### Requirement: Read-only Principal override
A Principal flagged `read_only` SHALL be denied every write permission — create, edit, remove, revive, and purge — on every entity of every Entity Kind, regardless of Group membership, ownership, holding a Purge Grant, or superuser status. This override SHALL be checked ahead of every other write rule (ownership-based edit permission, Purge Grant, global-admin status). Read access SHALL be entirely unaffected: a read-only Principal reads exactly as any other authenticated Principal does.

The flag SHALL normally be managed through Django admin by an authorized non-read-only operator. A Principal SHALL be allowed to read its own flag through `/api/me/` but SHALL NOT change it through a public self-service endpoint. An audited infrastructure recovery command SHALL be the only additional operator management path in this change.

#### Scenario: Read-only Group member cannot edit their own Group's entity
- **WHEN** a Principal flagged `read_only` who is a member of Group *G* attempts to edit a manual entity owned by *G*
- **THEN** the request is rejected, even though plain Group membership would otherwise authorize it

#### Scenario: Read-only Group member cannot create an entity in their own Group
- **WHEN** a Principal flagged `read_only` who is a member of Group *G* attempts to create a new entity owned by *G*
- **THEN** the request is rejected

#### Scenario: Read-only superuser cannot write
- **WHEN** a Principal flagged `read_only` who also holds `is_superuser` status attempts to edit, create, remove, revive, or purge any entity
- **THEN** every such request is rejected

#### Scenario: Read-only Purge Grant holder cannot purge
- **WHEN** a Principal flagged `read_only` who holds a Purge Grant for Group *G* attempts to purge a `removed` entity owned by *G*
- **THEN** the request is rejected

#### Scenario: Read-only Principal reads normally
- **WHEN** a Principal flagged `read_only` lists or retrieves any entity
- **THEN** the request succeeds exactly as it would for a non-read-only authenticated Principal

### Requirement: Read-only covers all user-initiated mutation surfaces
Core SHALL deny read-only user operations that change catalog data, relationships, tags, settings, access controls, or plugin state, including adopt, custom actions, and requests that enqueue mutating work. This requirement SHALL apply to direct APIs, services acting for the caller, and Django admin, regardless of staff/superuser status or selected evaluator. Denial SHALL occur before persistence, external side effects, or job enqueueing and SHALL return HTTP 403 for authenticated HTTP mutation attempts. Read permissions SHALL remain subject to their existing rules and SHALL NOT be expanded by read-only status.

#### Scenario: Read-only superuser edits settings directly
- **WHEN** a read-only superuser posts a tag-color, catalog-home, or other configuration mutation directly
- **THEN** the operation returns 403 without changing data even when the old guard checked only is_superuser

#### Scenario: Caller starts mutating work
- **WHEN** a read-only Principal invokes a plugin action that would enqueue a mutation job
- **THEN** no job or partial mutation is created

#### Scenario: Queued work outlives a privilege change
- **WHEN** a job initiated by a writable Principal starts its mutation after that Principal became read-only
- **THEN** it rechecks the initiating Principal and performs no mutation

### Requirement: Django admin cannot bypass the account restriction
Read-only staff and superusers SHALL be denied admin add/change/delete operations, inline writes, bulk actions, and custom mutation views across registered models, including users, AccountAccess, membership and permission grants. Admin view access SHALL follow existing permissions. A read-only administrator SHALL NOT clear its own flag, delete its AccountAccess row, or use admin authentication/break-glass as a write exemption.

#### Scenario: Read-only administrator removes its own restriction
- **WHEN** a read-only administrator submits a crafted UserAdmin inline update or deletion for its AccountAccess
- **THEN** the request is rejected and the restriction remains in force

#### Scenario: Read-only administrator invokes a bulk action
- **WHEN** a read-only administrator invokes a mutating admin action or custom mutation view
- **THEN** no records or jobs are changed, regardless of superuser status

### Requirement: Flag administration is authorized and audited
Normal flag changes SHALL require a non-read-only operator with explicit AccountAccess change permission and authority over the target User. Creation/change/deletion of the flag state SHALL record operator, target, old/new values, and timestamp atomically with the change. Creating an intended read-only account and its flag SHALL commit atomically before that account can authenticate. Deletion that restores the default false state SHALL receive equivalent authorization and audit; the normal inline UI SHALL use explicit false instead of deletion. An infrastructure-only recovery command SHALL require exact target and reason, offer safe dry-run output, and audit its action without exposing a callable web bypass.

#### Scenario: Operator creates a read-only account
- **WHEN** an authorized operator creates a User with read_only enabled
- **THEN** no successfully committed intermediate state allows that account to authenticate without the restriction

#### Scenario: Non-read-only operator removes a restriction
- **WHEN** an authorized non-read-only operator clears the flag
- **THEN** the change and its audit event commit together and ordinary authorization rules resume

#### Scenario: All writable administrators are unavailable
- **WHEN** an infrastructure operator executes the documented recovery command with exact target and reason
- **THEN** the selected restriction can be removed with an audit record, without permitting a read-only browser session to perform the same operation

### Requirement: Existing sessions observe current account restrictions
Core SHALL read current persisted AccountAccess state at each new request's authorization boundary and before user-triggered job mutations. After a flag change commits, subsequent such checks across all sessions/workers SHALL observe it without requiring reauthentication. Missing rows SHALL mean false; storage failures SHALL fail closed rather than be treated as missing rows. The flag SHALL NOT be authoritative session-cached state. Already committed or already authorized in-flight work is not required to be retroactively cancelled.

#### Scenario: Operator restricts an already logged-in user
- **WHEN** the operator sets read_only and an existing session next attempts a write
- **THEN** it receives 403 even if its frontend still shows writable controls

#### Scenario: Restriction is removed
- **WHEN** the flag is cleared and an existing session requests a write
- **THEN** normal permission evaluation resumes and the request is not automatically allowed

### Requirement: Authentication and service maintenance remain available
Read-only SHALL restrict user-initiated mutations, not all database writes or unsafe HTTP methods. Login/logout, session maintenance, audit, Core-controlled identity/profile/group provisioning, and explicitly supported credential recovery/change flows SHALL continue under their own security policies without permitting AccountAccess changes. Independently scheduled system ingestion SHALL retain its service authorization; a user request SHALL NOT impersonate that service or select a source parameter to bypass read-only.

#### Scenario: Read-only user authenticates and logs out
- **WHEN** the user completes a supported authentication or logout flow
- **THEN** required session and audit changes succeed while catalog mutations remain denied

#### Scenario: User attempts to impersonate ingestion
- **WHEN** a read-only caller supplies a system/ingestion source value to a mutation operation
- **THEN** it does not bypass the caller's restriction

### Requirement: Identity providers and membership changes preserve read-only
Authentication providers, external claims/groups, profile synchronization, identity linking, and automatic provisioning SHALL NOT assign, clear, overwrite, or delete AccountAccess. All identities linked to one Principal SHALL share its restriction. Manual/provider membership grants, Purge Grants, and admin break-glass SHALL NOT override it. When issuing an external account that must be read-only from first access, the documented procedure SHALL create the flagged Principal before linking and allowing its identity under preprovisioned policy; automatic unrestricted creation followed by later flagging SHALL not be presented as equivalent.

#### Scenario: Read-only user logs in through another provider
- **WHEN** an existing read-only Principal authenticates through a different linked identity or receives new external memberships
- **THEN** the flag remains set and write attempts are denied

#### Scenario: Membership storage is migrated
- **WHEN** legacy memberships become manual or provider-managed grants
- **THEN** read-only flags remain unchanged and no resulting grant authorizes a read-only Principal to write

#### Scenario: External read-only account is prepared
- **WHEN** an operator creates the flagged Principal, links its exact external identity and enables preprovisioned access
- **THEN** the first successful external login is already restricted without an unrestricted provisioning window
