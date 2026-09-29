---
title: Compatibility, packaging, and lifecycle
description: Declare version ranges honestly and understand the current boundary for packaging, upgrades, disablement, removal, and purge.
audience: [plugin-author]
page-type: guide
---

# Compatibility, packaging, and lifecycle

Atlas versions Core and each plugin independently. A descriptor declares its
plugin version and an `atlasCore` compatibility range. A distribution manifest
selects the plugin version, and Composer verifies it against the descriptor and
locked artifacts. Backend and frontend artifacts for one plugin must resolve to
the same version.

```python
compatibility = {"atlasCore": ">=0.1 <1"}
```

Composer currently resolves only workspace packages from the repository lock
files. The `atlas.plugins` entry-point group is reserved for future wheel
discovery. Atlas does not provide external package-publication infrastructure
or a published stable SDK, so this repository has no release-upload procedure
to document.

The authentication provider surface is independently identified by the
literal contract version `atlas.auth.providers.v1`. A provider descriptor must
declare that exact version, and composition/runtime registration rejects an
unknown version rather than partially activating it. Additive fields may be
introduced compatibly within v1 only when existing providers and consumers can
ignore them safely. Removing a field, changing its meaning, narrowing an
accepted value, or changing a protocol method requires a new provider contract
version and the corresponding Plugin API/Core compatibility change. A v1
provider remains selectable only while both its plugin's `atlasCore` range and
the installed Plugin API support v1.

## Change and upgrade safely

Release a plugin change with an honest compatibility range, update the
distribution manifest and lock together, review behavior changes, and follow
the [upgrade guide](../operating-atlas/upgrade.md). Deprecate a contract by
keeping a compatible path through the announced supported range; remove it
only in a planned incompatible change with migration and user-impact review.

## Disable, remove, reinstall, purge

`disabled` suppresses runtime registrations and frontend contributions while
keeping code, migrations, and data. Removal also preserves data. Reinstalling
or re-enabling restores compatible contributions. Purge is a separate,
irreversible operator command. It first reports scoped tables and row counts,
then deletes only with `--confirm` while the plugin is still selected.

```shell
cd core/backend
poetry run python manage.py purge_plugin atlas.inventory
poetry run python manage.py purge_plugin atlas.inventory --confirm
```

See [plugin lifecycle](../operating-atlas/plugin-lifecycle.md) for the
operator procedure and [models, migrations, and jobs](models-migrations-and-jobs.md)
for data responsibilities.
