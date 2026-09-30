---
title: Plugin configuration
description: Declare typed plugin settings, resolve secrets safely at startup, and expose only an explicit public projection to the frontend.
audience:
  - plugin-author
page-type: guide
---

# Plugin configuration

Use a plugin configuration schema when a plugin needs installation-specific
values. It defines the contract between the distribution manifest, the backend
process, and, for explicitly safe values, the frontend. A plugin reads neither
global Django settings nor `os.environ` directly.

## Audience, prerequisites, and outcome

This guide is for authors of a backend or full-stack plugin that is selected in
a [distribution](../configuration/distributions.md). You need a descriptor and
a Python package as described in [plugin layouts](plugin-layouts.md).

The outcome is a frozen, namespaced Pydantic configuration object that rejects
unknown fields, resolves secret references once during backend startup, and
supplies a deliberately small JSON-safe projection to frontend code.

## Declare a schema on the descriptor

Subclass `PluginConfigSchema`. Its Pydantic model is frozen and uses
`extra='forbid'`, so a misspelled or unsupported manifest field fails before a
plugin serves requests. Use ordinary field types for non-secret values. A field
that can contain a secret must include `SecretRef` in its type.

```python
from atlas_plugin_api import PluginConfigSchema, PluginDescriptor, SecretRef


class InventoryConfig(PluginConfigSchema):
    api_base_url: str
    refresh_minutes: int = 15
    api_token: str | SecretRef

    PUBLIC_FIELDS = frozenset({"api_base_url", "refresh_minutes"})


PLUGIN = PluginDescriptor(
    id="atlas.inventory",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("atlas_plugin_inventory",),
    entry_point="atlas_plugin_inventory.plugin:PLUGIN",
    config_schema=InventoryConfig,
)
```

Keep the schema in the plugin's public package, close to its descriptor. Do
not share an unnamespaced settings model between plugins: each selected plugin
receives only its own resolved schema instance. For the exact descriptor type,
see the [plugin contract reference](reference.md#declaring-a-plugin).

## Configure it in a distribution

The manifest carries a `config` block under the matching plugin entry. Values
are validated against `InventoryConfig` while the distribution is composed.
For a real credential, store the value in the deployment environment and put
only the environment-variable name in source control:

```yaml
plugins:
  - id: atlas.inventory
    version: 0.1.0
    backend: { package: atlas-plugin-inventory, source: workspace }
    config:
      api_base_url: https://inventory.example.internal
      refresh_minutes: 10
      api_token: { fromEnv: INVENTORY_API_TOKEN }
```

`{fromEnv: INVENTORY_API_TOKEN}` is a `SecretRef`, not the secret itself. Do
not put a production token in a manifest, lock file, checked-in example, or
frontend configuration. A literal is accepted only for a field whose schema
also accepts it; use that only for an intentionally non-secret development
value.

Validate the selected distribution before building it:

```shell
uv run --project composer atlas-compose resolve distributions/default/manifest.yaml -o distributions/default/lock.yaml
uv run --project composer atlas-compose validate distributions/default/manifest.yaml distributions/default/lock.yaml
```

See [composition errors](../operating-atlas/composition-errors.md) when schema
validation rejects a field, type, or plugin selection.

## Runtime resolution and backend use

Core validates the raw block during settings setup, resolves every `SecretRef`
once against the process environment, and stores the resulting object in the
central plugin configuration registry. It does not write the resolved value to
the manifest, lock, generated composition modules, or a response.

Read the typed instance through the registry after startup. Treat an absent
entry as a configuration or selection error:

```python
from server.apps.plugins.config import registry


config = registry.get("atlas.inventory")
if config is None:
    raise RuntimeError("atlas.inventory configuration was not registered")

assert isinstance(config, InventoryConfig)
client = InventoryClient(base_url=config.api_base_url, token=config.api_token)
```

`MissingSecretEnvError` names both the configuration field and the missing
environment variable. Set that variable in the backend process environment and
restart. Never log the secret value or replace the reference with a committed
literal. Centralized resolution keeps plugin code from accidentally serializing
or leaking secrets.

## Expose a public frontend projection

Nothing crosses to the browser by default. `PUBLIC_FIELDS` is an allow-list;
the backend calls `public_projection()` for every registered plugin and sends
only those fields in the public bootstrap configuration, keyed by plugin id.
`PluginConfigSchema` rejects a `PUBLIC_FIELDS` entry that is unknown or whose
type can hold `SecretRef`, even if the current value happens to be harmless.

The matching TypeScript types are intentionally JSON-only:

```ts
import type { BootstrapConfig, PluginPublicConfig } from '@atlas/plugin-api'

function inventoryConfig(config: BootstrapConfig): PluginPublicConfig | undefined {
  return config['atlas.inventory']
}
```

Treat this as display and UI-behavior configuration, not authorization or a
secret transport. The frontend must not infer permission from it; the backend
still enforces every protected action. See [frontend contributions](extension-points.md)
for the separate route and UI-composition contract.

## Validate the contract

Add focused tests beside the schema for unknown fields, `fromEnv` resolution,
missing environment variables, and the public projection. The repository's
contract tests exercise the same boundary:

```shell
cd core/backend
uv run pytest \
  ../../plugin-api/python/atlas_plugin_api/tests/test_config.py \
  server/apps/plugins/tests/test_config.py -q
```

## Failures and safe corrections

| Symptom | Cause | Safe correction |
| --- | --- | --- |
| Manifest validation rejects a field | The name is unknown, its value has the wrong type, or the plugin has no matching schema. | Correct the namespaced `config` block or evolve the schema deliberately; do not ignore unknown fields. |
| Startup reports `MissingSecretEnvError` | The `fromEnv` name is absent from the backend process environment. | Supply the named variable through the deployment secret mechanism and restart. |
| A secret appears in a browser response | A secret-capable field was incorrectly treated as public. | Remove it from `PUBLIC_FIELDS`; the schema should also type it as `… | SecretRef` so projection fails safely. |
| Frontend config is empty | The field was not explicitly listed in `PUBLIC_FIELDS`, or the plugin was not registered. | Expose only the non-sensitive value required by UI code and verify the plugin is selected. |
| Plugin code reads `os.environ` | Configuration is bypassing validation and centralized resolution. | Move the value into the plugin schema and retrieve the resolved instance from the registry. |

Next, use [permissions](../concepts/permissions.md) to protect any action that
uses this configuration, [backend collaboration](backend-collaboration.md) for
cross-plugin contracts, and the [environment reference](../configuration/environment-variables.md)
for Atlas-wide operator settings.
