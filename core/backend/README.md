# Atlas backend

For the full Docker development and production-like workflows, see the [root Atlas guide](../../README.md) and the canonical [Operating Atlas](https://sidorov-as.github.io/atlas/operating-atlas/) guide. It covers configuration, migrations, recovery boundaries, and troubleshooting.

## Host workflow

Copy the local environment, install dependencies with `uv`, then start Django:

```shell
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

The default database host is `localhost:5432`; adjust `DJANGO_DATABASE_HOST` and `DJANGO_DATABASE_PORT` in `.env` as needed. Set `CATALOG_TITLE` and `CATALOG_DESCRIPTION` to brand the homepage; when unset, they default to `Atlas` and `A software catalog for teams, systems, components, resources, and APIs.` respectively.

The authenticated `GET /api/catalog-configuration/` endpoint exposes those effective settings to catalog clients. `GET /api/diagrams/landscape/` renders the catalog-wide System Landscape as SVG by default; pass `format=png` for PNG and `download=1` for an attachment. These routes are included in the generated OpenAPI document alongside the existing entity-scoped diagram endpoints.

Run the backend test suite with `uv run pytest`.

For Compose logs, normal shutdown, and the explicitly scoped local-volume reset,
follow [Operations](https://sidorov-as.github.io/atlas/deployment/operations/).
Do not use the reset procedure for data that needs to be retained.

## Migration linting

New migrations (Core and every plugin) are checked for destructive operations — dropped column/table, or narrowing a field's nullability without a default — via [django-safe-migrations](https://django-safe-migrations.readthedocs.io/). Run it locally with:

```shell
uv run python -m django_safe_migrations.cli --baseline .migration-baseline.json
```

(`--baseline`, not `--diff <ref>`: the check runs against the committed baseline file, so it never depends on a fetched `origin/main` and produces the same verdict locally and in CI. See `--generate-baseline` in the same CLI to regenerate `.migration-baseline.json` after pruning fixed issues from it.)

(`-m django_safe_migrations.cli`, not the `check-migrations` console script — the console script doesn't add the current directory to `sys.path`, so it can't import `server.settings`.)

A flagged operation that's a genuine, reviewed maintenance-mode change can be marked inline with a required justification, which allows it through:

```python
operations = [
    # safe-migrations: ignore SM002 -- <why this drop is safe here>
    migrations.RemoveField(model_name="widget", name="legacy_field"),
]
```

`uv run python manage.py check_migration_boundaries` separately checks that a plugin's migrations depend only on Core's migrations and its own prior history, never another plugin's — both checks run in CI on every pull request that touches a migration (`.github/workflows/migration-lint.yml`).
