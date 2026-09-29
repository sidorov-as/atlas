## ADDED Requirements

### Requirement: Settings is restricted to administrators
The Settings area SHALL be accessible only to a superuser. A non-admin SHALL NOT see the "Settings" navigation item and SHALL be redirected away if they navigate to a Settings URL directly.

#### Scenario: Admin sees and can open Settings
- **WHEN** a superuser is logged in
- **THEN** the "Settings" navigation item is visible, and opening any `/settings/*` URL renders the corresponding section

#### Scenario: Non-admin does not see Settings
- **WHEN** an authenticated user who is not a superuser is logged in
- **THEN** the "Settings" navigation item does not appear

#### Scenario: Non-admin is redirected away from a direct Settings URL
- **WHEN** an authenticated user who is not a superuser navigates directly to a `/settings/*` URL
- **THEN** they are redirected away without seeing any Settings content

#### Scenario: UI gating is not the security boundary
- **WHEN** a non-admin's client calls a Settings-owned write endpoint directly, bypassing the UI
- **THEN** the backend rejects the request regardless of what the frontend would have shown

### Requirement: The frontend can determine whether the current user is an admin
The system SHALL expose an endpoint that reports whether the current authenticated user is a superuser, independent of the session/authentication endpoint's own user payload.

#### Scenario: Admin status is available after login
- **WHEN** an authenticated user's client queries the admin-status endpoint
- **THEN** it returns whether that user is a superuser, without requiring any Settings-specific request first

### Requirement: Settings is organized into nested sections
The Settings area SHALL present its sections (at minimum "Home" and "Tag colors") as distinct nested routes under `/settings/*`, each reachable via its own URL from a persistent sub-navigation, with `/settings` itself redirecting to the default section.

#### Scenario: Each section has its own URL
- **WHEN** an admin opens `/settings/tags`
- **THEN** the Tag colors section renders directly, without first navigating through a different Settings page

#### Scenario: Visiting the bare Settings URL redirects to a default section
- **WHEN** an admin navigates to `/settings`
- **THEN** they land on `/settings/home`
