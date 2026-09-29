## ADDED Requirements

### Requirement: Backend images include local PlantUML rendering dependencies
Both development and production backend image targets SHALL include the Java runtime and PlantUML executable required by `c4-diagrams` local rendering.

#### Scenario: Production backend can render locally
- **WHEN** the production backend image is built and starts in Compose
- **THEN** the diagram endpoint can invoke PlantUML locally without downloading a renderer or contacting a remote render service

#### Scenario: Development backend retains renderer after source mounting
- **WHEN** the development Compose topology bind-mounts backend source into its container
- **THEN** the installed PlantUML executable and Java runtime remain available to the reloading backend
