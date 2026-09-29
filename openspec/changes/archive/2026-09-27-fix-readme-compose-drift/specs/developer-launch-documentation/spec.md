## MODIFIED Requirements

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
