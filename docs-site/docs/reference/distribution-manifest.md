---
title: Distribution manifest and lock
description: Exact fields for selecting and locking Atlas Core and plugins.
audience: [operator, plugin-author]
page-type: reference
---

# Distribution manifest and lock

The manifest records the source-controlled desired selection. The lock is the
resolved, exact build input. Current Composer resolves `workspace` artifacts
only.

```yaml
distribution: { id: atlas.default, version: "2026.09" }
core: { version: 0.1.0 }
plugins:
  - id: atlas.inventory             # unique plugin id
    version: 0.1.0                  # must match resolved artifact
    disabled: false                 # optional; defaults false
    backend: { package: atlas-plugin-inventory, source: workspace }
    frontend: { package: "@atlas/plugin-inventory", source: workspace }
    config:                         # validated by the descriptor schema
      token: { fromEnv: INVENTORY_TOKEN }
```

`distribution.id` and `distribution.version` identify the build; `core.version`
is checked against plugin `atlasCore` ranges. Each plugin has an `id`, `version`,
at least one artifact, and optionally `disabled` and `config`. Artifact fields
are `package` and `source`; registry source names may be accepted by the schema but
are not currently resolved by this checkout. A `workspace` backend that is not in
`core/backend/uv.lock`, such as an example-only plugin, can add `path`, a
repo-relative directory whose `pyproject.toml` names the package; the lock then
records that directory's hash. `fromEnv` references an environment
variable and never puts the secret value in source control.

The lock records `distribution` as `id@version`, `core`, and plugins keyed by
`id@version`. Each selected backend has `package`, exact `version`, and
`hash`; each frontend has `package`, exact `version`, and `integrity`. Generate
the lock instead of editing it by hand:

```shell
uv run --project composer atlas-compose resolve distributions/default/manifest.yaml -o distributions/default/lock.yaml
uv run --project composer atlas-compose validate distributions/default/manifest.yaml distributions/default/lock.yaml
```

For procedures and failure correction, use [Assembling a distribution](../configuration/distributions.md)
and [composition errors](../operating-atlas/composition-errors.md).

## Authentication

`auth.providers` is an ordered, non-empty list of provider policy objects.
`auth.default` must name one selected id. Legacy string entries are rejected.

```yaml
auth:
  publicOrigin: https://atlas.example
  sessionMaxAgeSeconds: 28800
  trustedProxyAddresses: []
  adminPassword: {mode: disabled, principalIds: []}
  outboundTrust:
    allowedDestinations: [https://idp.example]
    allowDevelopmentHttp: false
  passwordPolicy:
    minimumLength: 15
    maximumLength: 128
    rejectCommon: true
    rejectUserSimilarity: true
  recovery:
    mode: operator-managed
    verifiedAddressesRequired: true
    tokenMaxAgeSeconds: 3600
  providers:
    - id: atlas.auth.oidc
      signup: disabled
      principalProvisioning: automatic
      actorProvisioning: automatic
      profileFields: [username, displayName, email]
      sourceBinding:
        sourceId: https://idp.example
        configurationFingerprint: reviewed-issuer-v1
      groupSync:
        mode: exact
        snapshotRequirement: required
        maxAgeSeconds: 28800
        mappings: {engineering: platform-owners}
      restrictedAttributes: []
  default: atlas.auth.oidc
```

| Provider field | Accepted values and behavior |
| --- | --- |
| `signup` | `disabled` or `enabled`; only local auth may enable it |
| `principalProvisioning` | `preprovisioned`, `automatic`, or `restricted` |
| `actorProvisioning` | `manual` or `automatic` |
| `profileFields` | Unique entries from `username`, `displayName`, and `email` |
| `restrictedAttributes` | Required only with `restricted`; each item names accepted `verified-ownership` or `authority-managed` provenance |
| `sourceBinding` | Non-empty immutable `sourceId` and non-secret `configurationFingerprint` |
| `groupSync.mode` | `none`, `additive`, or `exact` |
| `groupSync.snapshotRequirement` | `unsupported` for `none`; `best-effort` or `required` for additive; `required` for exact |
| `groupSync.maxAgeSeconds` | Positive finite freshness, default 28,800 seconds |
| `groupSync.mappings` | External value to existing Atlas Group; invalid with `none` |

`sessionMaxAgeSeconds` and recovery token age must be positive. `publicOrigin`
contains only scheme and authority and uses HTTPS outside loopback development.
Trusted proxy entries are IP addresses. Break-glass admin password login needs
a non-empty unique list of positive Principal ids. Password minimum is at least
15 and maximum at least 64.

The lock adds resolved public provider metadata and Core policy while keeping
secret references unresolved. It must never contain submitted credentials,
client/bind secrets, or tokens. See [authentication routes and diagnostics](authentication.md)
and [Choose an authentication method](../operating-atlas/authentication.md).
