# Operations

Every command below starts with `docker compose --env-file core/backend/.env`. Add
`-f docker-compose.dev.yml` when operating on the development topology.

## Migrations

```shell
docker compose --env-file core/backend/.env exec backend python manage.py migrate
```

New Core and plugin migrations are checked for destructive operations before merging. These
include dropping a column or table, or making a field non-nullable without a default. For a
reviewed maintenance-mode change, mark the flagged operation inline with the required
justification comment.

## Logs

```shell
docker compose --env-file core/backend/.env logs -f
```

## Shutdown

```shell
docker compose --env-file core/backend/.env down
```

Add `-f docker-compose.dev.yml` for the development topology.

For version changes, behavior changes, and the rollback boundary, follow
[Upgrade an Atlas distribution](../operating-atlas/upgrade.md). Release-specific behavior belongs
on that page, not here.

## Resetting local data

```shell
docker compose --env-file core/backend/.env down --volumes
```

!!! danger "Destructive, but scoped"
    This removes the topology's named Compose volumes, including its database and generated static
    data. Repository files remain untouched. Add `-f docker-compose.dev.yml` to reset development
    data. The two topologies use separate volumes.
