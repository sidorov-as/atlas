# Atlas Gitea authentication provider

`atlas.auth.gitea` is the first-party, provider-specific Gitea OAuth2 adapter.
Its supported baseline is django-allauth 65.19.1 and Gitea 1.27.3.

The adapter uses Authorization Code with mandatory PKCE S256, requests exactly
the `read:user` scope, reads the authenticated profile from `/api/v1/user`, and
uses the decimal Gitea `User.id` as the stable subject. The configured canonical
Gitea origin is the identity source namespace. OAuth scopes are never returned
as Atlas roles, permissions, or groups.

Team synchronization is deliberately unsupported in v1. Although Gitea exposes
`/api/v1/user/teams`, reliable exact synchronization would require the separate
`read:organization` scope and complete pagination. Deployments must configure
`groupSync.mode: none` and manage Atlas memberships independently.

Atlas logout always destroys the local Atlas session. This adapter advertises no
remote-logout capability because Gitea 1.27.3 has no validated end-session
contract for this integration; the upstream Gitea browser session may remain.
