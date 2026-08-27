# Authentication provider contract fixture

This deliberately separate Python package proves that a provider can consume
the `atlas.auth.providers.v1` contract-test kit without importing Atlas Core or
repository-private fixtures. Its provider imports only `atlas_plugin_api`; its
test supplies `CredentialProviderContractHooks` and calls
`run_credential_provider_contract`.

## Required hooks

A credential provider supplies factories for a fresh provider, bounded flow
context, valid credentials, invalid credentials, and a simulated unavailable
upstream. It also supplies equality-comparable snapshots of Core-owned
session/authorization state and of provider persistence. The suite verifies
descriptor identity, normalized and stable success, safe failures, unchanged
Core state, and absence of persisted credential values.

A redirect provider uses `RedirectProviderContractHooks`. Besides a fresh
provider and start context, it supplies callback factories for valid,
mismatched, expired, browser-mismatched, and unavailable cases. The suite also
checks replay rejection, atomic consumption by simultaneous callbacks, stable
subjects, and unchanged pre-login session/authorization state.

The generic suite cannot know a protocol's cryptographic rules. Adapter
authors must additionally test every property of their protocol and library:
for OIDC this includes PKCE S256, nonce, signature and allowed algorithm,
issuer, audience/authorized party, token time claims, UserInfo `sub` equality,
trusted JWKS rotation, and token endpoint behavior. OAuth adapters must test
their provider-specific subject, profile endpoint, scopes, PKCE, and callback
rules. Directory adapters must test TLS and destination policy, escaping,
anonymous/empty bind rejection, unique resolution, stable identifiers,
complete pagination, and deadline behavior.

Provider plugins are trusted server code. Passing these cooperative contract
tests does not sandbox a malicious or compromised package.

Run from this directory after installing the published Plugin API package:

```console
pytest
```

