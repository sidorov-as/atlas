## ADDED Requirements

### Requirement: Backend images contain no out-of-scope example or fixture source
Neither the `development` nor `production` target of `core/backend/Dockerfile`, nor `deploy/render/Dockerfile`, SHALL copy source from `examples/` into the image. Any source an image's build copies in SHALL belong to a dependency group that image's own `poetry install` invocation actually installs.

#### Scenario: Production image is built
- **WHEN** the `production` target of `core/backend/Dockerfile` or `deploy/render/Dockerfile` is built
- **THEN** the resulting image contains no files under an `examples/` path

#### Scenario: Development image is built
- **WHEN** the `development` target of `core/backend/Dockerfile` is built
- **THEN** `poetry install` succeeds without requiring any path under `examples/` to exist
