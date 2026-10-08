---
title: Fix distribution composition errors
description: Map Atlas composition failures to the manifest or plugin contract that must change.
audience:
  - operator
page-type: how-to
---

# Fix distribution composition errors

Run composition before building or deploying:

```shell
uv run --project composer atlas-compose resolve distributions/default/manifest.yaml -o distributions/default/lock.yaml
uv run --project composer atlas-compose validate distributions/default/manifest.yaml distributions/default/lock.yaml
```

For a custom installation, use a copied distribution path; the checked-in default files are Atlas's own distribution. Validation fails fast. Correct the named contract, then resolve a fresh lock. Do not edit generated composition modules.

| Failure category | Corrective action |
| --- | --- |
| Duplicate plugin identity | Keep one manifest entry for each plugin id. |
| Backend/frontend version mismatch | Resolve both artifacts at the declared plugin version. Do not hand-edit the lock; integrity comes from `uv.lock` and `package-lock.json`. |
| Core compatibility | Choose a plugin release whose `atlasCore` range contains the manifest core version, or select a compatible core. |
| Missing dependency or cycle | Add the required plugin at a compatible version, or remove or rework the dependency cycle in the plugin descriptors. |
| Duplicate kind, capability, permission, extension point, contribution, or route | Change the conflicting plugin-owned identifier or remove one contribution. Identifiers are global within a distribution. |
| Reserved/conflicting route | Give the frontend contribution a distinct non-reserved route. |
| Invalid configuration | Match the plugin descriptor's typed configuration shape. Supply secrets as `{fromEnv: NAME}` references instead of literal values. |
| Package-boundary failure | Remove the forbidden cross-plugin dependency. Use a declared capability, extension point, or direct public contract. |

The CLI validates manifest/lock structure and static composition. Runtime-only settings such as a missing environment secret must be corrected in the private deployment environment and verified through service logs after startup.

See [assembling a distribution](../configuration/distributions.md) and the [plugin contracts](../plugin-development/reference.md) for the related configuration and contract details.
