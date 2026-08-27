---
title: Plugin permissions
description: Declare permissions once, ask the selected policy evaluator, and enforce the same decision in the UI and backend.
audience: [plugin-author]
page-type: guide
---

# Plugin permissions

Use a permission when an action changes or reveals protected data. Atlas has one
distribution-wide policy evaluator. Plugins declare permission identifiers, and
that evaluator makes the authorization decision.

## Declare and register

Give a plugin permission a stable, namespaced id. Register it from
`register_runtime()`, not at import time. A duplicate id stops composition and
reports both owners.

```python
from atlas_plugin_api import PluginDescriptor, register_permission

WIDGET_EDIT = 'atlas.inventory.widget.edit'

def register_runtime() -> None:
    register_permission(WIDGET_EDIT, owner=PLUGIN.id)
```

## Enforce at the resource boundary

Pass the authenticated principal, the exact id, and the entity that owns the
resource to the evaluator. Deny access before a view mutates data. Hiding a UI
control is only a convenience; the backend must enforce the decision.

```python
from django.core.exceptions import PermissionDenied
from atlas_plugin_api import get_policy_evaluator

def update_widget(request, entity, payload):
    if not get_policy_evaluator().check(request.user, WIDGET_EDIT, entity):
        raise PermissionDenied('You cannot edit this widget.')
    # validate and persist payload
```

Use `resource=None` only when the action has no owning catalog entity. The
built-in RBAC evaluator grants authenticated users `*.read`, `*.create`, and
`*.delete`; an `*.edit` decision depends on membership in the entity owner.
This is current built-in policy, not a contract that plugins may reproduce.
See [Permissions](../concepts/permissions.md) for its full boundary and
[entity lifecycle](../using-atlas/manage-entity-lifecycle.md) for the separate
YAML-provenance write block.

## Gate the frontend too

Use the permission information exposed by Core to avoid presenting an action
that will fail. Keep the backend check, and do not infer access from plugin
configuration, ownership labels, or a visible route.

## Test the decision

Cover allowed and denied principals, an owner mismatch, and the backend route
or service boundary. Run the following test for the contract registry:

```shell
cd core/backend
poetry run pytest ../../plugin-api/python/atlas_plugin_api/tests/test_permissions.py -q
```

Next: [testing plugins](testing.md), [frontend contributions](extension-points.md), and the
[Python contract reference](reference.md#permissions-and-authorization).
