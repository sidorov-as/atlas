---
title: Manage read-only accounts
description: Restrict a Principal to its existing read access, audit the change, recover from operator lockout, and plan safe external-account issuance and rollback.
audience:
  - operator
page-type: task
---

# Manage read-only accounts

Use an account-wide read-only restriction when a Principal must keep its
ordinary catalog visibility but must not perform user-initiated mutations.
The restriction overrides owner-Group membership, Purge Grants, staff status,
and superuser status. It grants no new read permission.

This restriction is separate from an entity being managed by
`catalog-info.yaml`: the account flag limits what a Principal may do, while
YAML provenance controls how a particular entity is managed.

## Prerequisites and boundary

- Run the database migrations that create `AccountAccess` and its audit trail.
- To change the flag in Django administration, use a non-read-only operator
  who can change both the target User and `AccountAccess`.
- Use the infrastructure recovery command only from an initialized backend
  environment with controlled shell access.

Atlas enforces the current persisted flag at authorization boundaries. The UI
also hides write controls, but it is not the security boundary. A missing
`AccountAccess` row means unrestricted by this feature; a database error while
checking the flag fails closed.

## Set or clear the flag in Django administration

1. Sign in to `/admin/` as an authorized, non-read-only operator.
2. Open **Users**, then open the exact target User.
3. In **Account access**, set **Read only** to the intended value and save the
   User form.
4. Reopen the target User and verify the displayed value.
5. Inspect the corresponding `AccountAccessAuditRecord` through the approved
   database/audit tooling. It records the operator, target id and username,
   old and new values, action, and timestamp.

The User change and side-car audit record commit in one transaction. The
inline cannot delete the side-car row: clear the checkbox to restore ordinary
authorization. A read-only administrator cannot change any admin-managed
state or clear its own restriction, even with a crafted request.

## What the affected user observes

`GET /api/me/` reports the current state as `isReadOnly`. The frontend refreshes
it after login, when the page regains focus or visibility, on entry to a write
route, and after a denied write. Existing browser sessions do not need to log
in again.

The next authorization check after setting the flag denies user-initiated
catalog, relationship, tag, settings, access-control, admin, and installed
plugin mutations before their side effects. Clearing the flag restores the
normal evaluator decision; it does not grant a write that the account could
not otherwise perform.

Login, logout, session maintenance, security audit, Core-controlled identity
or profile provisioning, supported credential-security flows, and independently
scheduled ingestion keep their existing service policies. They cannot change
`AccountAccess`, and a caller cannot claim a service/source identity to bypass
the restriction.

An operation already authorized and in flight when the flag commits is not
retroactively cancelled. Previously committed work is not undone. Future
user-triggered background jobs must retain the initiating Principal and check
the current flag again before mutation; the current distribution has no such
user-triggered job dispatcher.

## Recover when every writable operator is locked out

`clear_read_only` is an infrastructure-only escape hatch. It is a dry run by
default and requires the exact username and a non-blank audit reason. From
`core/backend`, preview the change first:

```shell
poetry run python manage.py clear_read_only exact-username \
  --reason "approved incident or ticket reference"
```

Confirm that the output names the expected username, numeric id, current and
proposed values, and reason. Apply the same exact operation only after that
review:

```shell
poetry run python manage.py clear_read_only exact-username \
  --reason "approved incident or ticket reference" \
  --confirm
```

The confirmed change is transactional and creates an audit record whose
operator is empty and whose reason is prefixed with `infrastructure recovery`.
There is no equivalent browser or public API operation. Use `--set true` only
when an approved infrastructure procedure deliberately sets, rather than
clears, the restriction.

## External accounts that must be read-only on first access

Atlas supports first-access read-only issuance through preprovisioning. Follow
this order; allowing automatic provisioning before the flag and exact link
exist creates a writable window and is not equivalent:

1. Atomically create the Principal with `read_only=true` through the operator
   workflow.
2. Preview and then create the exact identity link. Use identifiers from the
   trusted provider administration surface, never an email or display name:

   ```bash
   poetry run python manage.py manage_auth_identity link \
     --provider atlas.auth.oidc \
     --source https://idp.example \
     --subject 248289761001 \
     --principal-id 42 \
     --reason "approved read-only external access"

   poetry run python manage.py manage_auth_identity link \
     --provider atlas.auth.oidc \
     --source https://idp.example \
     --subject 248289761001 \
     --principal-id 42 \
     --reason "approved read-only external access" \
     --apply
   ```

3. Configure that provider with `principalProvisioning: preprovisioned` before
   permitting login. Do not use `automatic` for this issuance workflow.
4. Verify that a missing link is denied, then verify first-login read success
   and direct-write rejection.

Provider claims, profile updates, identity linking, manual/provider membership
grants, Purge Grants, and administrator break-glass preserve the side-car
unchanged and cannot override it. The identity-link command cannot set or clear
`read_only`; use the audited account operator workflow for that state.

## Security-sensitive rollback

Once any account is flagged, deploying a version that ignores
`AccountAccess` silently restores its write privileges. Before rollback,
export and review the affected Principals and choose one of these controls:

- keep an equivalent mandatory write guard in the rollback version; or
- block/deactivate every affected account before the old code can serve
  authenticated requests.

Preserve the `AccountAccess` and audit data through forward and reverse
migrations. Do not drop the table, recreate rows with defaults, or describe a
schema rollback as harmless. After the deployment, test a flagged owner,
superuser, and Purge Grant holder against a direct write, not only the UI.

## Verify the result

With the target account's existing session, confirm that a permitted catalog
read still behaves normally and a direct API write returns `403` with no
partial state or queued work. Then clear the flag and verify that the same
write returns to ordinary permission evaluation rather than becoming
unconditionally allowed.

See [Permissions](../concepts/permissions.md) for the authorization model,
[Auth and identity](../concepts/auth-and-identity.md) for Principal/Actor
separation, and [Upgrade](upgrade.md) for the general schema rollback boundary.
