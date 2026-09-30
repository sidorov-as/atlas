---
title: Migrate and revoke authentication state
description: Move local and experimental OIDC deployments to authoritative selection, source binding, finite sessions, and source-aware grants.
audience: [operator]
page-type: runbook
---

# Migrate and revoke authentication state

Back up the database and retain the old manifest and lock before changing
authentication. Resolve the new lock in a staging copy and test a selected
fallback before changing production.

## Release migration checklist

Complete this checklist against a staging restore before upgrading production.

- [ ] Record the running Atlas version and retain the old Deployment Manifest,
  Distribution Lock, generated backend/frontend configuration, and a restorable
  database backup from the same maintenance window.
- [ ] Replace legacy provider strings with policy-bearing entries. Select at
  least one provider, set exactly one `auth.default`, set `publicOrigin`, and
  choose finite session and exact-group freshness limits.
- [ ] For local-only deployments, select `atlas.auth.local`, keep
  `signup: disabled`, and preserve `principalProvisioning: preprovisioned` plus
  `actorProvisioning: manual` unless a reviewed policy change is intended.
- [ ] For experimental OIDC deployments, replace the deprecated
  `OIDC_ISSUER` discovery-URL alias with `OIDC_DISCOVERY_URL`, add the exact
  `OIDC_EXPECTED_ISSUER`, and move the client secret to a backend-only
  `{fromEnv: ...}` reference. Do not copy its resolved value into the manifest
  or lock.
- [ ] Update the identity provider registration to the exact callback
  `/auth/browser/v1/providers/atlas.auth.oidc/callback` under `publicOrigin`.
  Remove obsolete callback registrations only after the new callback succeeds.
- [ ] Preview and apply verified source-link migrations by exact provider,
  source, subject, and Principal ids. Classify or explicitly acknowledge every
  retained legacy grant before enabling exact reconciliation.
- [ ] Verify local or external login, repeated stable identity resolution,
  Principal/Actor linking, one allowed action, one denied action, logout, and
  selected fallback access. Verify anonymous signup remains closed.
- [ ] Verify issuer replacement, unverified restricted attributes, inactive
  Principals, session revoke-all, incomplete groups, and provider outage all
  fail closed without partial state.
- [ ] Keep the previous database backup and artifacts until the maximum old
  session age and exact-grant freshness window have elapsed and audit output has
  been reviewed.

Rollback is an infrastructure recovery, not a silent provider downgrade. Stop
traffic, restore the matched database/manifest/lock/generated-artifact set, and
keep affected Principals blocked until source and revocation generations are
known to be enforced. If the membership-grant reverse migration is used instead
of restoring a backup, it reconstructs only currently effective Actor/Group
pairs; provider provenance, expiry, and independent grant reasons are lost.
Test the selected local break-glass or alternate provider after rollback before
reopening traffic. Never re-enable local signup or an unselected provider as an
automatic fallback.

## Local-only deployments

1. Replace legacy string provider entries with an object for
   `atlas.auth.local` and set it as `auth.default`.
2. Set `signup: disabled` unless self-registration is an intentional policy.
3. Set Principal provisioning to `preprovisioned` and Actor provisioning to
   `manual` to preserve conservative behavior.
4. Configure the finite session lifetime, password/recovery policy, public
   origin, and explicit admin password policy.
5. Bootstrap or verify a controlled local administrator. Test login, closed
   signup, a protected API request, a denied unauthorized write, and logout.

## Experimental OIDC deployments

1. Select the `atlas.auth.oidc` plugin and provider explicitly.
2. Rename the old discovery setting to `discoveryUrl`, add an exact
   `expectedIssuer`, and register the Atlas callback under `publicOrigin`.
3. Move the client secret to a `{fromEnv: ...}` reference and configure
   scopes, claims, source binding, outbound destinations, and provisioning.
4. Inspect historical identity links. Never infer a missing source from the
   first new login. Preview and apply an exact source migration when the
   historical issuer is verified.
5. Classify legacy membership grants before enabling exact reconciliation.
6. Test issuer mismatch, callback, repeated stable login, mapping removal,
   fallback, finite session behavior, and logout.

## Change an identity source

Changing an OIDC issuer, Gitea instance, or directory namespace creates a new
authority. Preview a source migration using exact identifiers:

```shell
uv run python manage.py manage_auth_identity source-migrate \
  --provider atlas.auth.oidc \
  --source https://old-idp.example \
  --to-source https://new-idp.example \
  --subject 248289761001 \
  --operator-id 7 \
  --reason 'reviewed issuer migration'
```

Repeat with `--apply` only after reviewing collision counts and the target
source binding. Reselection or rollback does not resurrect explicitly revoked
links, sessions, or grants.

## Revoke access

Preview an exact link revocation, then apply it:

```shell
uv run python manage.py manage_auth_identity revoke \
  --provider atlas.auth.oidc --source https://idp.example \
  --subject 248289761001 --operator-id 7 \
  --reason 'employment ended'
```

Revocation invalidates that link's sessions and provider grants and leaves a
marker that blocks automatic recreation. Restoration is explicit and does not
restore old grants. Blocking or deactivating the Principal rejects every
session on the next request. A local password reset/change advances the
Principal's durable revoke-all generation and invalidates its existing
sessions across workers.

Upstream removal alone is not immediate deprovisioning. Without a local
action, detection waits for another provider verification and existing access
is bounded by session age and exact-grant freshness. Additive grants remain
until operator removal or source/link revocation.

## Rollback boundary

An older build is unsafe if it ignores source/revocation generations, closed
signup, explicit admin recovery, or assigned `AccountAccess` restrictions.
Keep affected accounts blocked during infrastructure recovery. Reversing the
grant migration preserves current effective pairs but loses provenance and
expiry. Restore a tested backup when that loss is unacceptable.
