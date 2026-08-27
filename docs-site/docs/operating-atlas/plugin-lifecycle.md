---
title: Change plugin lifecycle safely
description: Disable, remove, reinstall, and understand the irreversible data boundary for a selected plugin.
audience:
  - operator
page-type: how-to
---

# Change a plugin's lifecycle

Choose selected plugins when building the distribution. A running container cannot change its selection.

## Disable or re-enable

Set `disabled: true` on a selected plugin entry, resolve and validate the lock, rebuild, then restart. Disabled code remains installed: its Django app and migrations remain available, but runtime contributions and registered jobs are suppressed. Set `disabled: false` (or remove the field), resolve, validate, rebuild, and restart to restore those contributions against the preserved data.

## Remove and reinstall

To remove functionality, delete the plugin entry, resolve and validate, rebuild, and restart. This does not reverse migrations or erase data. Catalog entities whose kind provider is absent become unavailable and read-only; their identity and relationships are retained. Reinstall a compatible plugin and deploy the new distribution to restore supported behavior against that data.

## Purge boundary

Atlas does not expose a distribution-level "purge plugin data" command or a generic preview/confirmation workflow. Do not delete database tables, volumes, or migration records to simulate one. Purge is supported only for eligible removed catalog entities through the catalog lifecycle and requires a Purge Grant or superuser authority; see [Manage an entity lifecycle](../using-atlas/manage-entity-lifecycle.md).

Before any intentional destructive local reset, stop and follow the scoped warning in [operations](../deployment/operations.md#resetting-local-data).
