## ADDED Requirements

### Requirement: Write affordances are hidden for a read-only session
When the current session is flagged read-only (`/api/me/`'s `isReadOnly`), the frontend SHALL hide every write affordance this capability otherwise shows to an authenticated user, on top of (not instead of) the existing manual/YAML-managed distinction: the "Add <Kind>" action on the Systems, Components, Resources, and APIs list pages; the write entries in row-level context menus on the Systems, Components, Resources, APIs, and Teams list tables; the Edit/Remove/Revive/Purge action row on every entity detail page; and the Add/Edit forms themselves, whose routes SHALL redirect away a read-only session that navigates to them directly, the same "UI guard, not the security boundary" way `AdminProtected` already redirects a non-admin away from `/settings/*`. This is a UX affordance only — the backend write-permission check (catalog-auth spec's read-only override) remains the actual boundary regardless of what the frontend shows.

#### Scenario: Read-only session sees no Add action
- **WHEN** a read-only session opens the Systems, Components, Resources, or APIs list page
- **THEN** the "Add <Kind>" action is not shown

#### Scenario: Read-only session sees no row-level actions control
- **WHEN** a read-only session views a row on the Systems, Components, Resources, APIs, or Teams list table
- **THEN** no write action is shown for that row; menus containing permitted read/export/navigation actions retain those entries, regardless of manual/YAML-managed origin

#### Scenario: Read-only session sees no detail-page write actions
- **WHEN** a read-only session opens the detail page of any entity
- **THEN** no Edit, Remove, Revive, or Purge action is shown

#### Scenario: Read-only session is redirected away from a create or edit URL
- **WHEN** a read-only session navigates directly to a create or edit form URL for any entity kind
- **THEN** they are redirected away without seeing the form

#### Scenario: UI gating is not the security boundary
- **WHEN** a read-only session's client calls a write endpoint directly, bypassing the UI
- **THEN** the backend rejects the request regardless of what the frontend would have shown

#### Scenario: Non-read-only session is unaffected
- **WHEN** an authenticated session that is not flagged read-only opens any list or detail page
- **THEN** every write affordance this capability already defines renders exactly as it does today

### Requirement: Account access presentation refreshes safely
The current-user endpoint SHALL expose isReadOnly from current persisted state. The frontend SHALL refresh access state on session initialization/login, focus or visibility return, entry to a mutation route, and after a write-denied response. While required access state is unknown or failed to load, write controls/forms SHALL not be presented as authorized. Stale UI SHALL not defeat backend denial; no real-time push requirement is introduced.

#### Scenario: Open form becomes read-only
- **WHEN** an operator flags the account while its form is already open and submission is denied
- **THEN** the frontend refreshes access state, reports the denial, and prevents continued writable interaction without falsely claiming the submission succeeded

#### Scenario: Write route is loading access state
- **WHEN** the current access state has not loaded successfully
- **THEN** the mutation form is not rendered as available

### Requirement: Administrative and custom mutation controls obey read-only
All installed core/plugin write controls and pure mutation routes SHALL obey isReadOnly, including relationship editors, tags, configuration/settings, and user-triggered mutation jobs. Mixed read/write pages SHALL preserve allowed read content while hiding mutation controls. Pure mutation routes SHALL redirect to a safe read destination. This SHALL apply even when isAdmin is true and SHALL not alter per-entity YAML provenance rules.

#### Scenario: Read-only administrator opens settings
- **WHEN** a read-only account with ordinary permission to view settings opens a mixed settings page
- **THEN** permitted read content remains visible but editing, saving, and mutation-trigger controls are absent

#### Scenario: Menu contains read and write actions
- **WHEN** a read-only user opens an action menu with navigation/export and mutation entries
- **THEN** permitted read actions remain and mutation entries are hidden
