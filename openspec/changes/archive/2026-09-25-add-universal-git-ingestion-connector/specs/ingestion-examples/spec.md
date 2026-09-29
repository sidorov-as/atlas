## ADDED Requirements

### Requirement: Ingestion examples are isolated runnable Compose projects
The repository SHALL contain `examples/ingestion/` with at least one runnable example that stands up a self-hosted git service (Gitea) and demonstrates repository registration and ingestion against it. The example SHALL declare its own Compose file, `.env.example`, git-service and repository fixtures, and README, reusing repository build inputs without depending on another example's running services.

#### Scenario: Reader starts the example
- **WHEN** a reader follows the documented startup commands in `examples/ingestion/README.md`
- **THEN** the stack starts, Gitea is populated with fixture repositories containing `catalog-info.yaml` manifests, and Atlas has already ingested them by the time the reader opens it

#### Scenario: Compose configuration is rendered
- **WHEN** CI runs `docker compose config` for the ingestion example with documented placeholder values
- **THEN** the project resolves successfully without requiring an untracked secret file

### Requirement: The example documents a complete operator journey
The example README SHALL state audience, architecture, prerequisites, exact startup and cleanup commands, how to sign in to Gitea, how to sign in to Atlas both via Gitea OAuth login and via Django `/admin/` (including any bootstrap step Django admin access requires), how to edit a `catalog-info.yaml` manifest directly in the Gitea web UI, how to re-run an ingestion pass, and how to verify the resulting entity in the catalog.

#### Scenario: Reader completes the example
- **WHEN** a reader follows the example README on a supported development machine
- **THEN** they can start the topology, sign in to both Gitea and Atlas, locate a fixture repository's `catalog-info.yaml` in the Gitea UI, and reach the verification step without needing information absent from the README

#### Scenario: Django admin access is not left implicit
- **WHEN** the example README describes registering a repository or inspecting ingestion state through Django admin
- **THEN** it also documents the specific bootstrap step that grants Django admin access, rather than assuming a superuser account already exists

### Requirement: Owner Groups are pre-created before ingestion runs
Because `catalog-info.yaml` cannot declare a Group, the example SHALL create every owner Group its fixture manifests reference before any ingestion pass runs, through an operator-visible bootstrap step, and the README SHALL document that step explicitly rather than leaving it implicit.

#### Scenario: Fixture manifest references an existing Group
- **WHEN** the example's ingestion pass runs for the first time
- **THEN** every `spec.owner` reference in its fixture manifests already resolves to a Group created by the documented bootstrap step

### Requirement: The example demonstrates a live manifest-edit round trip
The example SHALL demonstrate that editing a `catalog-info.yaml` file directly in the git service's web UI and re-running ingestion updates the corresponding catalog entity, without requiring any change to Atlas configuration.

#### Scenario: An edited manifest is reflected after re-ingestion
- **WHEN** a reader edits a fixture repository's `catalog-info.yaml` in the Gitea web UI and then runs the documented re-ingestion command
- **THEN** the corresponding entity's detail page reflects the edited field
