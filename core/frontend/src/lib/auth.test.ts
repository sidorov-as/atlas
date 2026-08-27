// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  AuthenticationError,
  getAuthenticationBootstrap,
  login,
  startRedirect,
} from './auth'

afterEach(() => {
  vi.unstubAllGlobals()
  document.cookie = 'csrftoken=; Max-Age=0; path=/'
})

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('Atlas authentication gateway client', () => {
  it('loads the Atlas bootstrap instead of allauth provider discovery', async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse({
      providers: [],
      defaultProviderId: 'atlas.auth.local',
      providerChoiceUrl: '/login?choose-provider=1',
    }))
    vi.stubGlobal('fetch', fetch)

    await getAuthenticationBootstrap()

    expect(fetch).toHaveBeenCalledWith('/auth/browser/v1/config', expect.any(Object))
  })

  it('submits credentials to the selected provider and refreshes current access state', async () => {
    document.cookie = 'csrftoken=token; path=/'
    const fetch = vi.fn()
      .mockResolvedValueOnce(jsonResponse({
        data: { user: { id: 1, display: 'Person', username: 'person' } },
        meta: { is_authenticated: true },
      }))
      .mockResolvedValueOnce(jsonResponse({ isAdmin: false, isReadOnly: true }))
    vi.stubGlobal('fetch', fetch)

    const session = await login('example.credentials', { username: 'person', password: 'secret' })

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      '/auth/browser/v1/providers/example.credentials/credentials',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ credentials: { username: 'person', password: 'secret' } }),
      }),
    )
    expect(session.isReadOnly).toBe(true)
  })

  it('starts redirects through the provider-specific gateway and preserves the return path', async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse({
      redirectUrl: 'https://idp.example/authorize',
      correlationId: 'safe-id',
    }))
    vi.stubGlobal('fetch', fetch)

    await expect(startRedirect('example.oidc', '/systems?owned=1')).resolves.toBe(
      'https://idp.example/authorize',
    )
    expect(fetch).toHaveBeenCalledWith(
      '/auth/browser/v1/providers/example.oidc/start',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ returnUrl: '/systems?owned=1' }),
      }),
    )
  })

  it('exposes only sanitized gateway failure data to callers', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({
      error: {
        category: 'provider_unavailable',
        stage: 'redirect_start',
        correlationId: 'safe-id',
        retryable: true,
      },
    }, 503)))

    const error = await startRedirect('example.oidc', '/').catch((reason: unknown) => reason)

    expect(error).toBeInstanceOf(AuthenticationError)
    expect(error).toMatchObject({ category: 'provider_unavailable', correlationId: 'safe-id', retryable: true })
    expect((error as Error).message).not.toContain('upstream')
  })
})
