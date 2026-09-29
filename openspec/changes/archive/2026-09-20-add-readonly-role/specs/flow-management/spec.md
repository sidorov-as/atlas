## ADDED Requirements

### Requirement: Write affordances are hidden for a read-only session
`FlowDetailPage`'s Edit and Delete actions, the Flows list Add action, and its per-row write actions (both outside `EntityDetailShell`/`EntityListPage`, so not covered by `catalog-web-ui`'s equivalent requirement) SHALL be hidden for a read-only session, and the Flow create/edit form route SHALL redirect a read-only session away, the same way `catalog-web-ui`'s write-affordance requirement gates the core-shell-backed entity kinds.

#### Scenario: Read-only session sees no Edit/Delete on a Flow detail page
- **WHEN** a read-only session opens a Flow's detail page
- **THEN** neither the Edit nor the Delete action is shown

#### Scenario: Read-only session sees no row actions on the Flows list
- **WHEN** a read-only session views a row on the Flows list table
- **THEN** no write action is shown for that row while permitted read/navigation actions remain

#### Scenario: Read-only session is redirected away from a Flow create or edit URL
- **WHEN** a read-only session navigates directly to `/flows/new` or `/flows/:id/edit`
- **THEN** they are redirected away without seeing the form

#### Scenario: Non-read-only session is unaffected
- **WHEN** an authenticated session that is not flagged read-only opens a Flow detail page or the Flows list
- **THEN** Edit/Delete and row actions render exactly as they do today

#### Scenario: Read-only session sees no Flow Add action
- **WHEN** a read-only session opens the Flows list
- **THEN** the Add action is absent

#### Scenario: Flow mutation bypasses the UI
- **WHEN** a read-only Principal invokes a Flow mutation directly
- **THEN** the backend returns 403 before persistence or other mutation side effects
