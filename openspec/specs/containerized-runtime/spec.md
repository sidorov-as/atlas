## Purpose

Provide reproducible development and production-like Docker Compose runtimes
for the complete Atlas application.

## Requirements

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

### Requirement: Backend images include local PlantUML rendering dependencies
Both development and production backend image targets SHALL include the Java runtime, Graphviz executable, and PlantUML executable required by `c4-diagrams` local rendering.

#### Scenario: Production backend can render locally
- **WHEN** the production backend image is built and starts in Compose
- **THEN** the diagram endpoint can invoke PlantUML and Graphviz locally without downloading a renderer or contacting a remote render service

#### Scenario: Development backend retains renderer after source mounting
- **WHEN** the development Compose topology bind-mounts backend source into its container
- **THEN** the installed PlantUML executable, Java runtime, and Graphviz executable remain available to the reloading backend

### Requirement: Application containers run as a non-root user
The backend image (used for both the Django backend service and the ingestion worker, in both the `development` and `production` build stages) SHALL run its application process as a non-root user.

#### Scenario: Backend container process is non-root
- **WHEN** the backend service container starts from either the `development` or `production` image
- **THEN** its application process runs as a non-root user rather than `root`

#### Scenario: Ingestion worker container process is non-root
- **WHEN** the ingestion worker container starts from the same backend image
- **THEN** its process runs as a non-root user rather than `root`

#### Scenario: Development bind-mount workflow still works
- **WHEN** a developer starts the documented source-mounted development topology after this change
- **THEN** the backend container still reads and writes the mounted source directory successfully under the non-root user

### Requirement: Backend images contain no out-of-scope example or fixture source
Neither the `development` nor `production` target of `core/backend/Dockerfile`, nor `deploy/render/Dockerfile`, SHALL copy source from `examples/` into the image. Any source an image's build copies in SHALL belong to a dependency group that image's own `uv sync` invocation actually installs.

#### Scenario: Production image is built
- **WHEN** the `production` target of `core/backend/Dockerfile` or `deploy/render/Dockerfile` is built
- **THEN** the resulting image contains no files under an `examples/` path

#### Scenario: Development image is built
- **WHEN** the `development` target of `core/backend/Dockerfile` is built
- **THEN** `uv sync` succeeds without requiring any path under `examples/` to exist
