---
title: Reconcile external Group membership
description: Configure group mappings, grant ownership, freshness, exact synchronization, and legacy migration.
audience: [operator]
page-type: guide
---

# Reconcile external Group membership

External groups become ordinary Atlas membership only through explicit
`groupSync.mappings`. Unknown values are ignored. Atlas does not create Groups
from provider data or interpret a name such as `admin` as an administrative
role.

## Reconciliation modes

| Mode | Required snapshot | Add missing mapped grants | Remove omitted provider grants | Retention |
| --- | --- | --- | --- | --- |
| `none` | Unsupported | No | No | Membership stays operator-managed |
| `additive` | Best-effort or required | Yes | No | Retained until operator removal or source/link revocation |
| `exact` | Complete | Yes | Yes, only for the authenticating identity link | Expires after `maxAgeSeconds`, eight hours by default |

A complete empty snapshot removes that link's exact grants. Missing, partial,
unavailable, malformed, or oversized data fails exact provisioning and does
not renew existing freshness. Activity and login through another provider do
not extend an exact grant.

An effective Actor-to-Group membership can have several grants: manual,
legacy manual, or provider-owned. Removing one grant preserves access while
another applicable grant exists. Exact sync never deletes a manual grant or a
grant owned by another identity link.

## Configure mappings

```yaml
auth:
  providers:
    - id: atlas.auth.oidc
      groupSync:
        mode: exact
        snapshotRequirement: required
        maxAgeSeconds: 28800
        mappings:
          engineering: platform-owners
```

Create the target Atlas Group before login. After login, inspect grant source,
identity link, external key, last confirmation, expiry, and applicability.
Then verify a permitted action on a resource owned by the mapped Group and a
denied action on another resource.

## Migrate legacy memberships safely

The data migration preserves each historical Actor/Group pair as a manual
`legacy-unclassified` grant. It does not guess ownership from names or claims.
List unresolved grants:

```shell
poetry run python manage.py check_membership_grants
```

For each reviewed grant, either retain it as manual or transfer it to the
exact identity that should own it. Both forms preview by default:

```shell
poetry run python manage.py classify_membership_grant 123 \
  --as-manual --reason 'confirmed operator-managed'

poetry run python manage.py classify_membership_grant 123 \
  --identity-link-id 45 --external-key engineering \
  --reason 'historical OIDC membership'
```

Repeat the reviewed command with `--apply`. Do not enable exact sync until
every legacy grant is classified or explicitly retained. Test removal of a
transferred provider grant and confirm that any independent manual grant still
works.

The reverse schema migration reconstructs at most one currently effective
Actor/Group pair. It loses source ownership, confirmation time, and expiry.
Exercise forward and reverse migration against a backup before production
rollout.
