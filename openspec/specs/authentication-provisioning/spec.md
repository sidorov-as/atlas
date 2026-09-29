# authentication-provisioning Specification

## Purpose
Define secure, auditable identity linking, Principal and Actor provisioning, profile synchronization, and externally managed Group membership reconciliation.

## Requirements

### Requirement: External identity linking uses a provider and source scoped stable subject
Authentication Core SHALL key an external identity by `(provider_id, source_id, subject)` and SHALL maintain at most one link from that identity to one Principal. Email address, username, display name, mutable directory DN, or group membership SHALL NOT replace the stable subject unless the provider contract explicitly guarantees that value is immutable and unique.

#### Scenario: Repeated external login reuses the Principal
- **WHEN** the same provider id, source id, and subject authenticate after profile attributes have changed
- **THEN** Core reuses the existing Principal and updates only fields permitted by the configured profile policy

#### Scenario: Same subject from different providers
- **WHEN** two providers return the same textual subject value
- **THEN** Core treats them as distinct external identities unless an operator-controlled linking policy explicitly joins them

#### Scenario: Identity is already linked to another Principal
- **WHEN** provisioning would attach an existing provider-source-subject link to a different Principal
- **THEN** authentication is stopped with a safe conflict and no link is silently reassigned

### Requirement: Principal provisioning policy is explicit
Every external provider SHALL use an operator-selected Principal provisioning policy of `preprovisioned`, `automatic`, or `restricted`. Core SHALL apply that policy after provider verification and before session establishment. Restricted eligibility SHALL be checked on every login, including existing linked Principals; it SHALL NOT be merely a first-registration filter.

#### Scenario: Preprovisioned identity is absent
- **WHEN** a verified external identity has no existing link and the policy is `preprovisioned`
- **THEN** login is rejected without creating a User or ExternalIdentityLink

#### Scenario: Automatic provisioning creates a Principal
- **WHEN** a previously unseen verified identity authenticates under `automatic`
- **THEN** Core creates one Principal, records its external identity link, and uses it for the new session

#### Scenario: Restricted provisioning denies an ineligible identity
- **WHEN** a new or previously linked verified identity does not satisfy the configured domain or normalized-attribute restriction
- **THEN** Core rejects login without persisting a Principal, Actor, membership, or session

### Requirement: Actor provisioning policy is explicit
Every external provider SHALL use an operator-selected Actor provisioning policy of `manual` or `automatic`. Authentication SHALL remain distinguishable from catalog identity: a Principal can authenticate without an Actor only when `manual` is selected, and ownership-based permissions SHALL remain unavailable until an Actor is linked.

#### Scenario: Manual Actor provisioning
- **WHEN** a new Principal is created under `actorProvisioning=manual`
- **THEN** no Actor is created, login may complete, and ownership checks fail until an operator or ingestion links an Actor

#### Scenario: Automatic Actor provisioning
- **WHEN** a new or existing Principal without an Actor authenticates under `actorProvisioning=automatic`
- **THEN** Core creates exactly one Actor using normalized profile data, links it to the Principal, and makes it available to subsequent group reconciliation

#### Scenario: Existing unlinked Actor has matching display data
- **WHEN** automatic provisioning finds an Actor with a similar username, email, or display name but no explicit account link
- **THEN** Core does not silently claim that Actor and instead creates a distinct Actor or reports an operator-resolvable conflict according to the configured collision policy

### Requirement: External profile updates are policy-controlled
Core SHALL distinguish immutable identity fields from mutable profile fields and SHALL update only the profile fields the deployment explicitly delegates to the provider from a fixed set of supported non-security profile fields. Passwords, recovery destinations without independent verification, active/blocked status, `read_only`, staff/superuser flags, identity links, and authorization fields SHALL NOT be selectable profile fields. A provider SHALL NOT overwrite operator-managed Atlas data outside that allowlist.

#### Scenario: Provider-controlled display name changes
- **WHEN** a linked identity logs in with a changed display name and that field is provider-managed
- **THEN** the configured Principal or Actor display field is updated without changing the identity link

#### Scenario: Operator-managed field differs
- **WHEN** external profile data differs from a field not delegated to the provider
- **THEN** Core preserves the Atlas value

### Requirement: Group mapping targets existing Atlas Groups by explicit rules
External group values SHALL be processed only by Core's configured mapping policy. The policy SHALL match only explicitly configured external values to existing Atlas Groups and SHALL ignore unknown values; implicit exact-name matching is not enabled in v1. External data SHALL NOT create Groups, Purge Grants, permissions, staff status, or superuser status.

#### Scenario: Known external group maps to Atlas Group
- **WHEN** a verified identity carries an external group value covered by a configured mapping and has a linked Actor
- **THEN** Core creates ordinary Actor membership in the mapped existing Atlas Group

#### Scenario: Unknown external group is returned
- **WHEN** a verified identity carries a group value with no configured match
- **THEN** Core ignores it, records a safe diagnostic, and grants no access

#### Scenario: External group resembles an admin role
- **WHEN** a provider returns `admin`, `superuser`, or another elevated-looking value without an explicit ordinary Group mapping
- **THEN** no Django administrative flag, Purge Grant, or permission is created

### Requirement: Membership reconciliation mode is explicit
Every group-capable provider SHALL declare reconciliation mode `none`, `additive`, or `exact`. Core SHALL record ownership by external identity link (provider, source, and subject) so that reconciliation affects only that link's grants and never removes manual grants or grants from another identity. Effective membership SHALL require at least one unexpired applicable grant. Exact mode SHALL require a complete group snapshot and fail closed on missing, unavailable, malformed, or partial data; an explicitly complete empty snapshot SHALL remove that identity's grants.

#### Scenario: Group reconciliation is disabled
- **WHEN** mode is `none`
- **THEN** authentication leaves all Atlas Group memberships unchanged

#### Scenario: Additive reconciliation receives fewer groups
- **WHEN** mode is `additive` and a subsequent login omits a previously mapped group
- **THEN** Core retains the existing membership and adds any newly mapped memberships

#### Scenario: Exact reconciliation receives fewer groups
- **WHEN** mode is `exact` and a subsequent login omits a group whose membership was previously managed by that provider
- **THEN** Core removes the authenticating identity's stale grants while retaining manual grants and grants from other identities

#### Scenario: Reconciliation fails midway
- **WHEN** an error occurs while applying an exact group set
- **THEN** no partial membership set is committed and login fails without a new session; v1 provides no fail-open option and does not extend existing grant expiry

### Requirement: Provisioning and reconciliation are auditable
Core SHALL emit an audit record for Principal creation, Actor creation/linking, external identity conflicts, provider-managed profile changes, and group membership additions/removals. Audit data SHALL identify the provider and normalized action without recording credentials, tokens, raw claims, or secrets.

#### Scenario: Exact sync removes membership
- **WHEN** exact reconciliation removes an Actor from an externally managed Group membership
- **THEN** the audit trail records the provider, Principal/Actor, Group, action, and timestamp

#### Scenario: Audit record is inspected
- **WHEN** an operator inspects authentication provisioning history
- **THEN** no credential, access token, ID token, client secret, bind password, or unfiltered claim document is present

### Requirement: Logout semantics are explicit per provider
Core SHALL always terminate the local Atlas session. A provider MAY additionally declare supported remote logout behavior, which SHALL be documented and invoked only through its public contract; lack of remote logout SHALL NOT be described as IdP-wide sign-out.

#### Scenario: Provider has no remote logout
- **WHEN** a user logs out of Atlas through a provider without remote logout support
- **THEN** the Atlas session ends and documentation/UI does not claim that the upstream provider session ended

#### Scenario: Provider supports remote logout
- **WHEN** a selected provider declares and successfully performs remote logout
- **THEN** Core first invalidates the Atlas session and then follows the validated provider logout response or redirect


### Requirement: Identity sources cannot be silently rebound
Each external identity SHALL include a non-empty immutable source identifier bound to the configured identity authority. OIDC SHALL use the validated issuer; Gitea and custom directory providers SHALL define an equivalent instance/directory namespace. Core SHALL verify the result source against registered configuration. Changing the authority under an existing provider id SHALL NOT reuse old identity links or grants. Existing links without source metadata SHALL require an operator-verified migration; an unverified source SHALL never be inferred from an incoming login.

#### Scenario: Issuer changes while subject stays the same
- **WHEN** an operator changes the OIDC issuer while retaining the provider id and the new issuer returns a previously seen sub
- **THEN** the identity belongs to the new source and cannot resolve to the old Principal without an explicit audited linking operation

#### Scenario: Provider returns an unexpected source
- **WHEN** a provider returns a source different from its configured authority
- **THEN** Core rejects the result before provisioning

### Requirement: Restricted eligibility uses explicit attribute trust
Restricted policy SHALL declare required normalized attributes and their accepted verification provenance. Email-domain restrictions SHALL require a verified email, a configured trusted authority, and exact comparison of the normalized domain; missing verification, malformed values, suffix tricks, or user-editable attributes without the required assurance SHALL fail closed. SDK metadata SHALL distinguish verified ownership, authority-managed attributes, and unverified self-asserted profile data. Email or username equality SHALL NOT automatically link or merge Principals, even when the email is verified.

#### Scenario: Unverified corporate-looking email
- **WHEN** an identity supplies an allowed-domain email without the required verified-ownership evidence
- **THEN** restricted login fails without creating or modifying identity state

#### Scenario: Existing user loses eligibility
- **WHEN** a linked identity no longer satisfies restricted eligibility at a later login
- **THEN** login fails and existing sessions and grants established by that link are revoked

#### Scenario: Profile matches a privileged account
- **WHEN** a new identity has the same email or username as an existing administrator
- **THEN** Core does not attach it to that account and creates a distinct eligible Principal or returns a safe collision

### Requirement: Identity link administration is explicit and recoverable
Atlas SHALL provide an operator-only management command to inspect, create, revoke, and explicitly migrate identity links by exact provider, source, subject, and Principal identifiers, including a dry-run preview. Mutations SHALL be audited and enforce uniqueness. Revoking a link SHALL retain a revocation marker that prevents automatic reprovisioning, invalidate its sessions, and remove its provider grants; restoring it SHALL require an explicit operator operation. Linking to an administrative Principal SHALL require an explicit privileged-target option and SHALL never happen through public login or signup.

#### Scenario: Preprovisioned user is prepared
- **WHEN** an authorized operator links a verified source/subject to the intended Principal using the documented command
- **THEN** that exact identity can authenticate under preprovisioned policy without creating a second Principal

#### Scenario: Revoked identity authenticates again
- **WHEN** a revoked identity verifies upstream while automatic provisioning is enabled
- **THEN** Core rejects login rather than recreating the link or a new account

### Requirement: Provisioning and reconciliation are safe under concurrency
Database uniqueness SHALL cover identity tuples, Principal-to-Actor linkage, and grant ownership keys. Core SHALL serialize updates for a Principal and its relevant identity links. A verification attempt SHALL carry a Core-issued attempt generation so an older upstream snapshot completing later cannot overwrite a newer accepted reconciliation. First-login races SHALL produce one Principal and Actor or a safe retryable failure, with no orphan records. Every provisioning failure SHALL roll back state and prevent session creation.

#### Scenario: Concurrent first login
- **WHEN** two verified requests for the same new identity provision concurrently
- **THEN** at most one Principal, identity link, and Actor are created and successful requests resolve to that same Principal

#### Scenario: Older group snapshot completes last
- **WHEN** a newer attempt removed a grant and an older attempt completes afterward
- **THEN** the older result cannot restore the removed grant or extend its validity

### Requirement: Exact membership grants have bounded freshness
Exact-mode grants SHALL expire after the configured finite group freshness interval, defaulting to eight hours from the last complete verified snapshot. Authorization, serializers, and membership editing SHALL use the same effective-membership semantics, excluding expired grants without depending on a cleanup job. Another provider's login, failed reconciliation, or ordinary API activity SHALL NOT refresh them. Provider/source removal and explicit identity revocation SHALL invalidate affected grants durably; reselection SHALL not resurrect them. Shortening configured freshness SHALL apply to existing grants from their last-confirmed time. Additive mode SHALL explicitly retain memberships until operator removal or source/link revocation and SHALL NOT be advertised as timely upstream deprovisioning.

#### Scenario: User continues using another provider
- **WHEN** an exact-mode grant expires while its Principal has a valid session from another provider
- **THEN** that expired grant no longer authorizes access, although independent valid grants remain effective

### Requirement: Legacy membership migration preserves access without concealing provenance
Existing undifferentiated memberships SHALL initially migrate to manual grants marked as legacy-unclassified. Atlas SHALL provide a dry-run report and audited operator command to classify reviewed grants as manual or transfer them to an exact external identity source without creating a residual manual grant. Migration SHALL NOT guess ownership from current group names or claims. Before enabling exact mode on a legacy deployment, an operator SHALL explicitly classify or acknowledge retained legacy grants; diagnostics SHALL report those that exact mode cannot revoke.

#### Scenario: Legacy OIDC membership is transferred
- **WHEN** an operator transfers a reviewed legacy membership to its external identity and a subsequent complete snapshot omits that group
- **THEN** exact reconciliation removes the transferred grant and no migrated manual duplicate preserves access

#### Scenario: Provenance is unknown
- **WHEN** a legacy membership cannot be attributed confidently
- **THEN** it remains manual with an explicit diagnostic and is not silently removed by exact sync

### Requirement: Failed authentication audit survives state rollback
Successful provisioning mutations SHALL be audited transactionally with their state changes. Authentication denials, link conflicts, revocations, and provisioning failures SHALL additionally produce secret-safe security events outside any rolled-back provisioning transaction. A failure to persist the required success audit SHALL fail login closed. Audit delivery failures SHALL have a safe operational signal and SHALL never convert a failed authentication into success.

#### Scenario: Provisioning transaction rolls back
- **WHEN** group reconciliation fails after tentative Principal creation
- **THEN** tentative state and success events roll back while a sanitized failure event with correlation id remains observable

### Requirement: Identity and grant lifecycle preserves AccountAccess
Login, profile synchronization, link administration, source migration, Actor provisioning, and membership-grant migration/reconciliation SHALL preserve the Principal's operator-managed AccountAccess state. They SHALL NOT set or clear read_only, delete/recreate its row with defaults, or map external claims/groups into it. New links to an existing Principal SHALL share its existing restriction. Manual/provider memberships and Purge Grants SHALL not supersede it; AccountAccess enforcement SHALL remain independent of effective-membership calculations.

#### Scenario: Repeat login contains role-like claims
- **WHEN** an existing read-only Principal logs in again with changed profile data or claims suggesting writable/admin status
- **THEN** AccountAccess remains unchanged and writes remain denied

#### Scenario: Another identity is linked to a read-only Principal
- **WHEN** an authorized operator adds a second exact identity link and the user authenticates through it
- **THEN** that session uses the existing read-only restriction without resetting account defaults

#### Scenario: Membership migration adds effective grants
- **WHEN** existing memberships migrate or synchronization adds new grants for a read-only Principal
- **THEN** the flag is preserved and the new effective memberships cannot authorize writes for that Principal

### Requirement: Preprovisioned read-only identity is restricted from first access
The supported external read-only issuance workflow SHALL create the Principal and its AccountAccess restriction atomically using the existing operator workflow, then link its exact provider/source/subject and permit access through preprovisioned policy. An absent link SHALL reject login. Identity-link commands SHALL not need or gain authority to change read_only. Automatic creation followed by later flagging SHALL not be presented as equivalent to restricted first access.

#### Scenario: First external login uses a prepared account
- **WHEN** a flagged Principal has its exact identity link and authenticates under preprovisioned policy
- **THEN** Core reuses that Principal, preserves the flag during Actor/group provisioning, and allows permitted reads but rejects writes from the first session

#### Scenario: Identity setup is incomplete
- **WHEN** an external identity attempts login under preprovisioned policy before its link exists
- **THEN** login is rejected rather than automatically creating an unrestricted replacement Principal
