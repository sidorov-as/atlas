---
title: Test a plugin
description: Use focused backend, frontend, composition, migration, and compatibility checks before selecting a plugin in a distribution.
audience: [plugin-author]
page-type: guide
---

# Test a plugin

Start with the smallest boundary, then verify that the selected distribution
can compose. The commands below use the repository's current toolchains.

| Concern | Check |
| --- | --- |
| Python unit/API behavior | `cd core/backend && uv run pytest <plugin tests> -q` |
| Plugin API contracts | `cd core/backend && uv run pytest ../../plugin-api/python/atlas_plugin_api/tests -q` |
| Frontend behavior | `cd core/frontend && npm test -- --run` |
| Frontend type/build boundary | `cd core/frontend && npm run build` |
| Composition | `uv run --project composer atlas-compose validate distributions/default/manifest.yaml distributions/default/lock.yaml` |
| Migration safety | `cd core/backend && uv run django-safe-migrations && uv run python manage.py check_migration_boundaries` |

## What to cover

- Unit-test schemas, pure contribution builders, registries, and domain rules.
- Exercise protected API behavior with allowed and denied principals.
- Test frontend rendering and interaction without treating a hidden control as
  authorization proof.
- Test composition failures: duplicate ids, missing dependencies, incompatible
  versions, configuration errors, and route collisions.
- Test an upgrade path for models and migrations, including a safe failure or
  recovery boundary where relevant.
- Test that a failing plugin request is isolated and an unavailable capability
  is handled rather than imported around.

Run the focused test path recorded next to the plugin before the broad suite.
For a new source-backed tutorial example, run the commands in its page's
validation section as well. See [debug plugins](debugging.md) when a check
fails.
