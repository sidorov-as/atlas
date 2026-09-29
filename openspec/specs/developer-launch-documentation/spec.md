## Purpose

Provide discoverable instructions for launching and operating the Atlas
application locally.

## Requirements

### Requirement: Authoritative full-stack launch guide
The root README SHALL remain the concise full-stack launch entry point by
documenting prerequisites, environment-file setup, exact commands for dev and
production-like Compose topologies, and the expected service URLs and health
check. It SHALL link to the canonical documentation-site Getting Started and
Operating Atlas guides for the complete walkthrough, verification,
configuration, and diagnostic procedures. Documented commands SHALL match
what each topology's Compose configuration actually automates: a step SHALL
NOT be presented as a required manual action in the primary launch path when
the corresponding Compose service already performs it automatically.

#### Scenario: First local startup
- **WHEN** a developer follows the root README from a fresh checkout with
  Docker installed
- **THEN** they can create the required environment file and open the running
  Atlas application without relying on an undocumented command

#### Scenario: Developer needs the complete launch walkthrough
- **WHEN** a developer reaches the end of the root README's concise launch
  procedure
- **THEN** they can follow a direct link to the canonical documentation-site
  guide for login, demo data, catalog verification, supported topologies, and
  troubleshooting

#### Scenario: Documented commands match Compose automation
- **WHEN** a Compose topology already performs a step automatically (for
  example, the dev topology's `migrate` service running database migrations
  before `backend` starts)
- **THEN** the root README's primary launch procedure does not instruct the
  developer to also perform that step manually

### Requirement: Component-specific guidance remains discoverable
The backend and frontend README files SHALL document their component-specific
host workflows and SHALL link to the root guide for Compose workflows.

#### Scenario: Developer starts from a component README
- **WHEN** a developer opens the backend or frontend README
- **THEN** they can find both its direct development command and a link to the
  authoritative full-stack instructions

### Requirement: Operational recovery instructions
The root README SHALL summarize migrations, logs, normal shutdown, and the
explicit command that removes local Compose data, and SHALL link to the
canonical Operating Atlas procedures for detailed diagnosis and recovery. The
documented reset command SHALL remain explicitly scoped and SHALL distinguish
the development and production-like topologies.

#### Scenario: Developer needs a clean local database
- **WHEN** a developer follows the documented reset procedure
- **THEN** they can remove the intended topology's local Compose data
  intentionally without an ambiguous or repository-wide destructive command

#### Scenario: Developer needs recovery beyond a local reset
- **WHEN** a developer encounters an initializer, migration, gateway,
  backend, ingestor, or database failure
- **THEN** the root README directs them to the canonical symptom-oriented
  operations and recovery guide
