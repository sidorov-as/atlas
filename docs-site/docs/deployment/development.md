# Development topology

The development topology mounts the source tree into the containers. Backend and frontend changes
are picked up without rebuilding.

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml up --build
```

A one-shot `migrate` service applies Core and selected-plugin migrations
before `backend` and `ingestor` start, so a fresh or reset database is ready
without a separate step. After pulling new migrations into an already-running
topology, apply them from a second terminal instead:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml exec backend python manage.py migrate
```

## Services

| Service | URL | Notes |
| --- | --- | --- |
| Frontend (Vite) | <http://localhost:5173> | Hot module reload on source changes |
| Backend API health check | <http://localhost:8000/healthz/> | |
| PostgreSQL | `localhost:5432` | override with `POSTGRES_HOST_PORT` |

The frontend development server proxies `/api`, `/_allauth`, and `/admin` to the backend. The
stack is available from one origin during development, and Django reloads when backend source
changes.

## Demo data

Populate the catalog with sample systems, components, technology tags, dependency flows, and
inline OpenAPI/AsyncAPI documents:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml exec backend python manage.py seed_booking_demo --yes
```

!!! warning "Destructive"
    This command clears and recreates the database. Omit `--yes` to confirm interactively.
