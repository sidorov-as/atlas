---
title: Declare a required service
description: Declare an external service a plugin needs, see it recorded in the lock and wired into generated deployment inputs, and let operators supply their own instance.
audience:
  - plugin-author
page-type: guide
---

# Declare a required service

Some plugins need a separate process, such as a search server. Declare it in the
plugin's static descriptor instead of asking operators to hand-write it. The composer
validates the declaration, records it in the lock, runs the service next to the
application and wires its address and key into your plugin's configuration.
`atlas.search-meilisearch` is the reference
(`plugins/search-meilisearch/backend/atlas_plugin_search_meilisearch/plugin.py`).

A plugin that declares nothing is unaffected: composition, lock and generated inputs
are the same as before.

## Declare the service

Add a `RequiredService` to `PluginDescriptor.required_services`:

```python
from atlas_plugin_api import PluginDescriptor, RequiredService

SERVICE = RequiredService(
    id="meilisearch",
    purpose="Search index for the Meilisearch engine adapter",
    image="getmeili/meilisearch:v1.12",
    port=7700,
    health_check=("curl", "-fsS", "http://localhost:7700/health"),
    config_keys={"address": "url", "secret": "key"},
    secret_env="MEILI_MASTER_KEY",
    data_path="/meili_data",
)

PLUGIN = PluginDescriptor(
    ...,
    config_schema=MyPluginConfig,
    required_services=(SERVICE,),
)
```

| Field | Meaning |
| --- | --- |
| `id` | Compose service name and address host. Lowercase letters, digits and dashes. Not `postgres`, `initializer`, `backend`, `ingestor` or `frontend` |
| `purpose` | One line shown in errors and generated comments |
| `image` | Image pinned by a tag other than `latest`, or by a digest |
| `port` | Port the service listens on; the generated address is `http://<id>:<port>` |
| `health_check` | Command run inside the container; exit 0 means healthy |
| `config_keys` | Maps `address`, and optionally `secret`, to field names of your `config_schema` |
| `secret_env` | Variable the container reads its key from. Set exactly when `config_keys` has `secret` |
| `data_path` | Optional absolute container path to keep on a named volume |

The descriptor is read before `django.setup()`, so a declaration is metadata only; it
never starts or contacts anything. Invalid values raise `ValueError` when the module
is imported.

## Accept the wired values

The fields named in `config_keys` must exist on the configuration schema. Make the
secret field `str | SecretRef | None` so the composer's reference validates:

```python
class MyPluginConfig(PluginConfigSchema):
    url: str
    key: str | SecretRef | None = None
```

The composer fills `url` with the generated address and `key` with
`{fromEnv: ATLAS_SERVICE_<ID>_KEY}`. A value the operator writes in `config:` always
wins. Read the resolved value with `get_plugin_config`, as described in [Plugin
configuration](plugin-configuration.md).

## What the composer does

1. `atlas-compose resolve` records each service in the lock under
   `<plugin-id>/<service-id>`, with the declaring plugin, pinned image, port, health
   check, data path and the names of the key variables. The same manifest always
   yields the same entries.
2. `atlas-compose generate backend` adds the address and key reference to the plugin's
   configuration in the generated settings.
3. `atlas-compose generate compose` writes an override file: the service with a health
   check and, for `data_path`, a named volume `<id>-data`. It adds the key variable to
   `backend` and `ingestor` and makes them wait for the service to be healthy.
4. `atlas-compose validate` fails when two selected plugins declare the same service
   id with different definitions (naming both), when a config key is not a schema
   field, or when the lock no longer matches the manifest.

If the declaring plugin is not selected or is disabled, nothing is generated.

## Secrets

The lock and generated files hold the name of the key's environment variable, never
its value. The operator exports `ATLAS_SERVICE_<ID>_KEY` in the deployment
environment; Compose fails to start with a message naming it when it is missing. Do
not put the secret in the public configuration projection.

## Let operators bring their own instance

No work is needed on your side. An operator marks the service external on the
plugin's manifest entry:

```yaml
- id: atlas.example
  version: 0.1.0
  backend:
    package: atlas-plugin-example
    source: workspace
  services:
    meilisearch:
      external: true
      address: http://meilisearch.internal:7700
```

The composer then generates no container or volume and wires the given address.
`external: true` without an address, or a service id the plugin does not declare,
fails composition.

## Verify

1. Select the plugin in a development manifest and run `atlas-compose resolve`. Check
   the `services:` section of the lock.
2. Run `atlas-compose generate compose` and confirm the service, volume and
   `depends_on` appear. Deselect the plugin and confirm they disappear.
3. Start the stack and confirm the service is healthy and the plugin connects.

See `examples/search-meilisearch/` for a manifest, lock and generated output. For
operators, [Run search on Meilisearch](../operating-atlas/search-meilisearch.md)
shows the same flow from the other side.
