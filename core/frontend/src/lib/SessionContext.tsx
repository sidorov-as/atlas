// Session-aware routing support: loads the allauth session
// once on mount and exposes it to the app, so routes can redirect to /login
// when unauthenticated instead of hitting a 401 from the API.
//
// `refresh()` re-fetches current access state (account access presentation
// refreshes safely) — called here on focus/visibility return, and expected
// to be called by mutation-route guards on entry and by write call sites
// after a write-denied (403) response. `error` tracks a failed refresh so
// consumers can treat "unknown or failed" the same as "not authorized" for
// deciding whether to render write controls, rather than assuming false.
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { getSession, login as loginRequest, logout as logoutRequest, type SessionState } from './auth'
import { onWriteDenied } from './api'

interface SessionContextValue {
  session: SessionState | null
  isLoading: boolean
  error: boolean
  login: (providerId: string, credentials: Readonly<Record<string, string>>) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionState | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(false)
  const isMountedRef = useRef(true)

  const refresh = useCallback(async () => {
    try {
      const state = await getSession()
      if (isMountedRef.current) {
        setSession(state)
        setError(false)
      }
    } catch {
      if (isMountedRef.current) setError(true)
    } finally {
      if (isMountedRef.current) setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    isMountedRef.current = true
    void refresh()
    return () => {
      isMountedRef.current = false
    }
  }, [refresh])

  useEffect(() => {
    const onFocusOrVisible = () => {
      if (document.visibilityState === 'visible') void refresh()
    }
    window.addEventListener('focus', onFocusOrVisible)
    document.addEventListener('visibilitychange', onFocusOrVisible)
    return () => {
      window.removeEventListener('focus', onFocusOrVisible)
      document.removeEventListener('visibilitychange', onFocusOrVisible)
    }
  }, [refresh])

  useEffect(() => onWriteDenied(() => void refresh()), [refresh])

  const login = useCallback(async (providerId: string, credentials: Readonly<Record<string, string>>) => {
    const state = await loginRequest(providerId, credentials)
    setSession(state)
    setError(false)
  }, [])

  const logout = useCallback(async () => {
    await logoutRequest()
    setSession({ isAuthenticated: false, user: null, isAdmin: false, isReadOnly: false })
    setError(false)
  }, [])

  const value = useMemo(
    () => ({ session, isLoading, error, login, logout, refresh }),
    [session, isLoading, error, login, logout, refresh],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext)
  if (!context) throw new Error('useSession must be used within a SessionProvider')
  return context
}
