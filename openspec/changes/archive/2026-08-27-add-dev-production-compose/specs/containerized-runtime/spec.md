## ADDED Requirements

### Requirement: Complete production Compose topology
The project SHALL provide a root `docker-compose.yml` that builds and starts
PostgreSQL, the Django backend, the ingestion worker, and a production frontend
gateway without source-code bind mounts.

#### Scenario: Fresh production-like startup
- **WHEN** an operator supplies the documented environment and runs the
  documented production Compose command
- **THEN** all four application services start with PostgreSQL data persisted in
  a named volume

### Requirement: Same-origin production gateway
The production frontend gateway SHALL serve compiled SPA assets with history
fallback and SHALL proxy Django API, authentication, and admin routes to the
backend on the internal Compose network.

#### Scenario: Browser uses the public application origin
- **WHEN** a browser loads the production frontend and requests an API route
- **THEN** the request remains on the frontend's public origin and reaches the
  backend without exposing a separate backend host port

#### Scenario: Direct SPA route refresh
- **WHEN** a browser requests a client-side application route that is not a
  static file or Django route
- **THEN** the gateway returns the SPA entry document

### Requirement: Ordered production initialization
The production topology SHALL wait for PostgreSQL health, run migrations and
static collection successfully through a one-shot initializer, and only then
start services that require the schema or static assets.

#### Scenario: Initializer failure blocks dependent services
- **WHEN** migrations or static collection exit unsuccessfully
- **THEN** backend, ingestor, and gateway startup is blocked and the initializer
  exposes the failed command through its container logs

### Requirement: Source-mounted development topology
The project SHALL provide `docker-compose.dev.yml` that runs backend and
frontend development servers from bind-mounted project directories while
preserving container-installed dependencies and persistent PostgreSQL data.

#### Scenario: Backend source edit in development
- **WHEN** a developer edits backend source while the documented dev topology
  is running
- **THEN** the development backend reloads without rebuilding its image

#### Scenario: Frontend source edit in development
- **WHEN** a developer edits frontend source while the documented dev topology
  is running
- **THEN** Vite hot reloads or refreshes the application without rebuilding its
  image

### Requirement: Stage-specific service images
The backend and frontend Dockerfiles SHALL expose development and production
targets such that production images run built artifacts rather than development
servers.

#### Scenario: Production frontend build
- **WHEN** the production Compose topology builds the frontend image
- **THEN** it runs a compiled static frontend rather than `npm run dev`

