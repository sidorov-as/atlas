# Deployment

Atlas provides two Docker Compose topologies that use the same images and environment file:
a source-mounted [development topology](development.md) for daily work and an immutable,
same-origin [production-like topology](production.md) for deployment-like environments.

Both read `core/backend/.env` (copied from `core/backend/.env.example`) and are started with
`docker compose --env-file core/backend/.env ...`. See [Environment Variables](../configuration/environment-variables.md)
for what belongs in that file.

- [Development topology](development.md): source-mounted with automatic reloading for local iteration
- [Production-like topology](production.md): immutable images, one gateway port, and no mounted source
- [Operations](operations.md): migrations, logs, shutdown, and local-data resets
- [Troubleshooting](troubleshooting.md): startup verification and common failures

!!! note "Host-only workflows"
    Both topologies run entirely in Docker. To run the backend or frontend directly on the host
    instead (no Compose), see `core/backend/README.md` and `core/frontend/README.md` in the
    repository.
