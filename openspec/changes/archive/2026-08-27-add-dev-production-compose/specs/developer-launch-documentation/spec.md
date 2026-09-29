## ADDED Requirements

### Requirement: Authoritative full-stack launch guide
The root README SHALL document prerequisites, environment-file setup, exact
commands for dev and production-like Compose topologies, and the expected
service URLs and health check.

#### Scenario: First local startup
- **WHEN** a developer follows the root README from a fresh checkout with
  Docker installed
- **THEN** they can create the required environment file and open the running
  Atlas application without relying on an undocumented command

### Requirement: Component-specific guidance remains discoverable
The backend and frontend README files SHALL document their component-specific
host workflows and SHALL link to the root guide for Compose workflows.

#### Scenario: Developer starts from a component README
- **WHEN** a developer opens the backend or frontend README
- **THEN** they can find both its direct development command and a link to the
  authoritative full-stack instructions

### Requirement: Operational recovery instructions
The root README SHALL document migrations, logs, normal shutdown, and the
explicit command that removes local Compose data.

#### Scenario: Developer needs a clean local database
- **WHEN** a developer follows the documented reset procedure
- **THEN** they can remove the local Compose data intentionally without an
  ambiguous or repository-wide destructive command

