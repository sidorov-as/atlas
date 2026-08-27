import { describe, expect, it } from 'vitest'
import type { AuthenticationBootstrapConfig, AuthenticationProviderBootstrap } from './index'

describe('authentication bootstrap contract', () => {
  it('represents selected credential and redirect provider presentation only', () => {
    const providers = [
      {
        id: 'atlas.auth.local',
        contractVersion: 'atlas.auth.providers.v1',
        flowKind: 'credentials',
        presentation: {
          displayName: 'Username and password',
          credentialFields: [
            { id: 'username', label: 'Username', kind: 'text', autocomplete: 'username' },
            { id: 'password', label: 'Password', kind: 'secret', autocomplete: 'current-password' },
          ],
        },
        remoteLogout: 'unsupported',
        isDefault: true,
        signupOpen: false,
      },
      {
        id: 'atlas.auth.oidc',
        contractVersion: 'atlas.auth.providers.v1',
        flowKind: 'redirect',
        presentation: { displayName: 'Company SSO' },
        remoteLogout: 'supported',
        isDefault: false,
      },
    ] satisfies readonly AuthenticationProviderBootstrap[]
    const config = {
      providers,
      defaultProviderId: 'atlas.auth.local',
      providerChoiceUrl: '/login?choose-provider=1',
    } satisfies AuthenticationBootstrapConfig

    expect(config.providers.map((provider) => provider.id)).toEqual([
      'atlas.auth.local',
      'atlas.auth.oidc',
    ])
    expect(JSON.stringify(config)).not.toContain('clientSecret')
    expect(JSON.stringify(config)).not.toContain('discoveryUrl')
  })
})
