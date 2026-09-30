---
title: Provision Principals and Actors
description: Configure external identity linking, Principal and Actor provisioning, profile ownership, and read-only first access.
audience: [operator]
page-type: guide
---

# Provision Principals and Actors

An external login moves through distinct records:

1. The provider verifies a stable subject within an immutable source.
2. Core resolves an External Identity link keyed by provider, source, and subject.
3. Core resolves or creates the Principal according to policy.
4. Standard Catalog resolves or creates a linked Actor according to policy.
5. Core updates only the profile fields delegated to the provider.
6. Core reconciles mapped membership grants, commits its audit records, and creates the session.

The transaction fails closed. A link collision, invalid result, Actor conflict,
or reconciliation failure creates no partial account or session.

## Principal modes

| `principalProvisioning` | New identity | Existing link | Use when |
| --- | --- | --- | --- |
| `preprovisioned` | Denied | Reuses the exact linked Principal | Operators must approve every identity before first login |
| `automatic` | Creates one Principal and link | Reuses the Principal | The upstream authority may create Atlas accounts |
| `restricted` | Creates only when all assurance requirements pass | Rechecks eligibility on every login | Automatic creation is limited to verified attributes such as an exact email domain |

Restricted email eligibility requires verified ownership from the configured
authority. A matching unverified or user-editable address fails closed. Atlas
never joins an external identity to an existing account by username or email.

## Actor modes

| `actorProvisioning` | Behavior |
| --- | --- |
| `manual` | Login may finish without an Actor. Ownership-based permissions remain unavailable until an operator links one. |
| `automatic` | Standard Catalog creates and links one Actor from allowlisted normalized profile data. It does not claim a similar unlinked Actor. |

The Actor is the catalog identity used for ownership and Group membership. The
Principal is the login account. Staff, superuser, Purge Grant, and read-only
state remain separate administrative controls.

## Profile field ownership

`profileFields` may contain `username`, `displayName`, and `email`. On each
login, Core updates only the selected fields. Passwords, recovery addresses,
active status, staff and superuser flags, `read_only`, identity links, and
authorization state cannot be provider-managed fields.

## Prepare a preprovisioned identity

Use exact identifiers and run a preview first:

```shell
uv run python manage.py manage_auth_identity link \
  --provider atlas.auth.oidc \
  --source https://idp.example \
  --subject 248289761001 \
  --principal-id 42 \
  --operator-id 7 \
  --reason 'approved workforce identity'
```

Review the target, then repeat with `--apply`. Add `--privileged-target` when
the target Principal is staff or superuser. The command refuses fuzzy matching
and a subject already attached to another Principal.

For an external account that must be read-only from its first request, create
the Principal and its `AccountAccess.read_only` state through the documented
operator workflow first. Link the exact identity second, then use
`preprovisioned`. Automatic creation followed by later restriction leaves a
writable interval. Verify one permitted read and one rejected write after the
first login. [Read-only accounts](read-only-accounts.md) owns that restriction.

## Inspect and audit

```shell
uv run python manage.py manage_auth_identity inspect \
  --provider atlas.auth.oidc \
  --source https://idp.example \
  --subject 248289761001
```

Provisioning audit records identify normalized actions, provider, source,
Principal or Actor, Group changes, and a correlation id. They exclude
credentials, tokens, raw claims, and upstream response bodies. Provider health
and safe failure categories are covered by the [authentication reference](../reference/authentication.md).
