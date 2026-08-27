// @vitest-environment jsdom
import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SessionProvider, useSession } from './SessionContext'
import { apiFetch } from './api'
import { getSession, login, logout, type SessionState } from './auth'

vi.mock('./auth', () => ({
  getSession: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}))

const WRITABLE_SESSION: SessionState = {
  isAuthenticated: true,
  user: null,
  isAdmin: false,
  isReadOnly: false,
}

function Probe() {
  const { session, error } = useSession()
  return <div>{error ? 'error' : session?.isReadOnly ? 'read-only' : 'writable'}</div>
}

function renderProvider() {
  return render(<SessionProvider><Probe /></SessionProvider>)
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('SessionProvider access refresh', () => {
  beforeEach(() => {
    vi.mocked(getSession).mockReset().mockResolvedValue(WRITABLE_SESSION)
    vi.mocked(login).mockReset()
    vi.mocked(logout).mockReset()
  })

  it('refreshes current access state when the window regains focus', async () => {
    vi.mocked(getSession)
      .mockResolvedValueOnce(WRITABLE_SESSION)
      .mockResolvedValueOnce({ ...WRITABLE_SESSION, isReadOnly: true })
    renderProvider()
    await waitFor(() => expect(getSession).toHaveBeenCalledOnce())

    act(() => window.dispatchEvent(new Event('focus')))

    await waitFor(() => expect(getSession).toHaveBeenCalledTimes(2))
    expect(screen.getByText('read-only')).toBeDefined()
  })

  it('loads current read-only state on a redirect callback landing', async () => {
    vi.mocked(getSession).mockResolvedValueOnce({ ...WRITABLE_SESSION, isReadOnly: true })

    renderProvider()

    await waitFor(() => expect(screen.getByText('read-only')).toBeDefined())
  })

  it('uses the freshly loaded access state returned after credential login', async () => {
    vi.mocked(login).mockResolvedValueOnce({ ...WRITABLE_SESSION, isReadOnly: true })

    function LoginProbe() {
      const { login: submit, session } = useSession()
      return (
        <button onClick={() => void submit('atlas.auth.local', { password: 'secret' })}>
          {session?.isReadOnly ? 'read-only' : 'sign in'}
        </button>
      )
    }
    render(<SessionProvider><LoginProbe /></SessionProvider>)
    await waitFor(() => expect(getSession).toHaveBeenCalled())

    screen.getByRole('button').click()

    await waitFor(() => expect(screen.getByText('read-only')).toBeDefined())
    expect(login).toHaveBeenCalledWith('atlas.auth.local', { password: 'secret' })
  })

  it('refreshes current access state when the document becomes visible', async () => {
    vi.stubGlobal('document', document)
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
    renderProvider()
    await waitFor(() => expect(getSession).toHaveBeenCalledOnce())

    act(() => document.dispatchEvent(new Event('visibilitychange')))

    await waitFor(() => expect(getSession).toHaveBeenCalledTimes(2))
  })

  it('refreshes after a rejected write so stale forms receive the new restriction', async () => {
    vi.mocked(getSession)
      .mockResolvedValueOnce(WRITABLE_SESSION)
      .mockResolvedValueOnce({ ...WRITABLE_SESSION, isReadOnly: true })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 403 })))
    renderProvider()
    await waitFor(() => expect(getSession).toHaveBeenCalledOnce())

    await act(async () => {
      await apiFetch('/api/things/1/', { method: 'PATCH', body: '{}' })
    })

    await waitFor(() => expect(getSession).toHaveBeenCalledTimes(2))
    expect(screen.getByText('read-only')).toBeDefined()
  })

  it('marks failed refreshes as unknown instead of retaining writable authorization presentation', async () => {
    vi.mocked(getSession)
      .mockResolvedValueOnce(WRITABLE_SESSION)
      .mockRejectedValueOnce(new Error('network down'))
    renderProvider()
    await waitFor(() => expect(screen.getByText('writable')).toBeDefined())

    act(() => window.dispatchEvent(new Event('focus')))

    await waitFor(() => expect(screen.getByText('error')).toBeDefined())
  })
})
