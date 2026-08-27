---
title: Gitea OAuth2 authentication
description: Configure Atlas's provider-specific Gitea browser authentication adapter.
audience: [operator]
page-type: how-to
---

# Configure Gitea OAuth2 authentication

Atlas supports Gitea through `atlas.auth.gitea`, a provider-specific adapter.
OAuth 2.0 alone does not define identity, profile, or groups, so this adapter
cannot be repointed at GitHub, GitLab, or an arbitrary OAuth server.

## Provider contract

The supported baseline uses Gitea 1.27.3 and Authorization Code with PKCE S256.
Atlas requests exactly `read:user`, reads `GET /api/v1/user`, and uses the
decimal form of immutable Gitea `User.id` as the subject. The source is the
configured canonical instance origin without a trailing slash. Login, email,
and display name are mutable profile fields.

Register this exact callback below the configured `auth.publicOrigin`:

```text
/auth/browser/v1/providers/atlas.auth.gitea/callback
```

Keep the client secret in a `{fromEnv: ...}` reference in the plugin's
namespaced configuration. Add the canonical Gitea origin to
`auth.outboundTrust.allowedDestinations`; production uses HTTPS. Resolve and
validate the lock after selecting the plugin and provider.

## Provisioning and membership

Choose Principal and Actor modes in the provider entry. Gitea v1 does not
retrieve and paginate `/api/v1/user/teams`, so its `groupSync.mode` must remain
`none`. The `read:user` scope and Gitea organization roles grant no Atlas
permission. Link the Actor and manage Atlas Group membership through an
operator workflow.

## Verify

1. Open `/login` or the explicit `/login?choose-provider=1` chooser.
2. Authorize the exact `read:user` scope in Gitea.
3. Confirm repeated login reuses one Principal, External Identity link, and Actor.
4. Verify an authenticated read and a denied write on a resource the Actor does not own.
5. End the Atlas session and confirm the protected route requires login.

Atlas logout does not end the Gitea browser session because the v1 adapter
does not support remote logout. A later login may not prompt for a password.

The [runnable Gitea example](https://github.com/sidorov-as/atlas/tree/main/examples/authentication/oauth2-gitea)
contains the complete disposable manifest, bootstrap, and smoke test.
