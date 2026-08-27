// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { AuthenticationBootstrapConfig } from '@atlas/plugin-api'
import { LoginPage } from './LoginPage'
import { getAuthenticationBootstrap, startRedirect } from '../lib/auth'
import { useSession } from '../lib/SessionContext'

vi.mock('../lib/auth', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/auth')>()
  return {
    ...actual,
    getAuthenticationBootstrap: vi.fn(),
    startRedirect: vi.fn(),
  }
})

vi.mock('../lib/SessionContext', () => ({ useSession: vi.fn() }))

const LOCAL = {
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
} as const

const OIDC = {
  id: 'atlas.auth.oidc',
  contractVersion: 'atlas.auth.providers.v1',
  flowKind: 'redirect',
  presentation: { displayName: 'Company SSO' },
  remoteLogout: 'supported',
  isDefault: false,
} as const

function bootstrap(
  providers: AuthenticationBootstrapConfig['providers'],
  defaultProviderId: string,
): AuthenticationBootstrapConfig {
  return { providers, defaultProviderId, providerChoiceUrl: '/login?choose-provider=1' }
}

const login = vi.fn()

function renderLogin(entry: string | { pathname: string; search?: string; state?: unknown } = '/login') {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter initialEntries={[entry]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/systems" element={<div>systems destination</div>} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  )
}

beforeEach(() => {
  vi.mocked(getAuthenticationBootstrap).mockReset()
  vi.mocked(startRedirect).mockReset().mockReturnValue(new Promise(() => {}))
  login.mockReset().mockResolvedValue(undefined)
  vi.mocked(useSession).mockReturnValue({
    session: { isAuthenticated: false, user: null, isAdmin: false, isReadOnly: false },
    isLoading: false,
    error: false,
    login,
    logout: vi.fn(),
    refresh: vi.fn(),
  })
})

afterEach(() => cleanup())

describe('LoginPage provider selection', () => {
  it('renders and submits the selected local credential provider', async () => {
    vi.mocked(getAuthenticationBootstrap).mockResolvedValue(bootstrap([LOCAL], LOCAL.id))
    renderLogin({ pathname: '/login', state: { from: { pathname: '/systems', search: '?owned=1' } } })

    fireEvent.change(await screen.findByLabelText('Username'), { target: { value: 'person' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'correct horse' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => expect(login).toHaveBeenCalledWith(LOCAL.id, {
      username: 'person',
      password: 'correct horse',
    }))
    expect(startRedirect).not.toHaveBeenCalled()
  })

  it('auto-starts a redirect-only default and exposes no local form', async () => {
    const redirectOnly = { ...OIDC, isDefault: true }
    vi.mocked(getAuthenticationBootstrap).mockResolvedValue(bootstrap([redirectOnly], OIDC.id))
    renderLogin()

    await waitFor(() => expect(startRedirect).toHaveBeenCalledWith(OIDC.id, '/'))
    expect(screen.queryByLabelText('Username')).toBeNull()
  })

  it('shows local primary and selected redirect options when local is default', async () => {
    vi.mocked(getAuthenticationBootstrap).mockResolvedValue(bootstrap([LOCAL, OIDC], LOCAL.id))
    renderLogin()

    expect(await screen.findByLabelText('Username')).toBeDefined()
    expect(screen.getByRole('button', { name: 'Sign in with Company SSO' })).toBeDefined()
    expect(startRedirect).not.toHaveBeenCalled()
  })

  it('suppresses redirect-default auto-start on the permanent provider-choice URL', async () => {
    const redirectDefault = { ...OIDC, isDefault: true }
    const localFallback = { ...LOCAL, isDefault: false }
    vi.mocked(getAuthenticationBootstrap).mockResolvedValue(
      bootstrap([redirectDefault, localFallback], OIDC.id),
    )
    renderLogin('/login?choose-provider=1')

    expect(await screen.findByLabelText('Username')).toBeDefined()
    expect(startRedirect).not.toHaveBeenCalled()
  })

  it('omits installed-but-unselected providers because only bootstrap entries render', async () => {
    vi.mocked(getAuthenticationBootstrap).mockResolvedValue(bootstrap([LOCAL], LOCAL.id))
    renderLogin()

    await screen.findByLabelText('Username')
    expect(screen.queryByText(/Company SSO/)).toBeNull()
  })

  it('turns a failed default redirect into a non-looping local fallback', async () => {
    const redirectDefault = { ...OIDC, isDefault: true }
    const localFallback = { ...LOCAL, isDefault: false }
    vi.mocked(getAuthenticationBootstrap).mockResolvedValue(
      bootstrap([redirectDefault, localFallback], OIDC.id),
    )
    vi.mocked(startRedirect).mockRejectedValue(new Error('That sign-in provider is temporarily unavailable.'))
    renderLogin({
      pathname: '/login',
      state: { from: { pathname: '/systems', search: '?owned=1', hash: '#team' } },
    })

    expect(await screen.findByText('That sign-in provider is temporarily unavailable.')).toBeDefined()
    expect(screen.getByLabelText('Username')).toBeDefined()
    expect(startRedirect).toHaveBeenCalledTimes(1)
    expect(startRedirect).toHaveBeenCalledWith(OIDC.id, '/systems?owned=1#team')
  })

  it('shows a sanitized callback failure and never re-enters the redirect loop', async () => {
    const redirectDefault = { ...OIDC, isDefault: true }
    vi.mocked(getAuthenticationBootstrap).mockResolvedValue(bootstrap([redirectDefault], OIDC.id))
    renderLogin('/login?choose-provider=1&auth-error=invalid_state&return-url=%2Fsystems%3Fowned%3D1')

    expect(await screen.findByText('The sign-in attempt expired or was already used. Please try again.')).toBeDefined()
    expect(startRedirect).not.toHaveBeenCalled()
  })

  it('returns an authenticated browser to the complete originally requested path', async () => {
    vi.mocked(useSession).mockReturnValue({
      session: { isAuthenticated: true, user: null, isAdmin: false, isReadOnly: false },
      isLoading: false,
      error: false,
      login,
      logout: vi.fn(),
      refresh: vi.fn(),
    })
    vi.mocked(getAuthenticationBootstrap).mockResolvedValue(bootstrap([LOCAL], LOCAL.id))
    renderLogin({ pathname: '/login', state: { from: { pathname: '/systems', search: '?owned=1' } } })

    expect(await screen.findByText('systems destination')).toBeDefined()
  })
})
