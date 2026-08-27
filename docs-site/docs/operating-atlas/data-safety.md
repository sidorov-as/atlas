---
title: Database changes and data safety
description: Apply migrations safely and understand Atlas's supported backup, restore, and reset boundary.
audience:
  - operator
page-type: how-to
---

# Database changes and data safety

## Supported migration procedure

The production-like topology runs `migrate --noinput` in the one-shot `initializer` before application services start; the development topology runs the same step in its own one-shot `migrate` service before `backend` and `ingestor` start. For an already-running development topology, apply new migrations with:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml exec backend python manage.py migrate
```

Use `showmigrations` to inspect status without changing data. Never fake applied migrations or edit database rows to bypass a failure. Atlas checks destructive migration patterns and plugin migration boundaries. A rejected migration requires a reviewed and documented maintenance decision. Do not bypass it.

## Backup and restore boundary

This repository does not include a checked-in backup or restore command, storage provider integration, point-in-time recovery procedure, or tested rollback automation. It cannot provide a portable backup and restore sequence. Before using a production-like topology for retained data, establish and test a PostgreSQL backup and restore procedure for the database service you operate. Include application downtime and compatibility checks, then verify the restored data. `docker compose down --volumes` is neither a backup nor a restore procedure; it destroys the named local Compose data.

After a migration or database recovery controlled by your platform procedure, verify service order, `ps`, `/healthz/`, `/healthz/plugins/`, and a logged-in catalog read before accepting traffic. Follow [troubleshooting](../deployment/troubleshooting.md) for failures.
