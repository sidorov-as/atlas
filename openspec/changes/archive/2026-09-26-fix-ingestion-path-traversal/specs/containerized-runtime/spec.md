## ADDED Requirements

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
