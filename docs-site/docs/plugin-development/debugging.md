---
title: Debug a plugin
description: Diagnose plugin failures by phase without bypassing composition, configuration, permission, or migration boundaries.
audience: [plugin-author]
page-type: guide
---

# Debug a plugin

Start with the phase that failed; do not “fix” a composition error by importing
another plugin's private module or hard-coding a secret.

| Symptom | First place to inspect | Safe correction |
| --- | --- | --- |
| Import or descriptor failure | `id`, `version`, `entry_point`, selected package | Keep descriptor metadata import-safe and correct the selected artifact. |
| Composition failure | manifest, lock, dependency/compatibility ranges | Run `atlas-compose validate`; correct the declared contract or collision. |
| Route/contribution collision | contribution id and route path | Give it a stable plugin namespace; do not overwrite another contribution. |
| Configuration failure | schema and `{fromEnv: ...}` name | Correct the schema/value or provide the process secret; never log it. |
| Permission denied | registered id, principal, resource | Check through `get_policy_evaluator()` at the backend boundary. |
| Migration failure | plugin app ownership and migration history | Use expand-contract sequencing and run both migration checks. |
| Job does not run | descriptor `job_ids`, scheduler registration, plugin lifecycle | Verify active selection; disabled plugins have declared jobs paused. |
| API failure | authenticated request, generated OpenAPI, backend logs | Reproduce the documented endpoint contract, then add a focused API test. |
| Missing frontend contribution | selected frontend package, generated composition, capability gate | Verify selection and the declared contribution; do not assume a backend plugin ships UI. |

Useful first commands:

```shell
uv run --project composer atlas-compose validate distributions/default/manifest.yaml distributions/default/lock.yaml
cd core/backend && uv run python manage.py check_migration_boundaries
```

For runtime symptoms, keep the original composition or request error in the
log and add a focused regression test before changing a public contract. See
[composition errors](../operating-atlas/composition-errors.md) and
[testing plugins](testing.md).
