import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { Loader } from '@gravity-ui/uikit'
import { useSession } from '../lib/SessionContext'

/** Route guard: redirects to /login (preserving the target) until a session is confirmed. */
export function RequireSession({ children }: { children: ReactNode }) {
  const { session, isLoading, error } = useSession()
  const location = useLocation()

  if (isLoading || error) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
        <Loader size="l" />
      </div>
    )
  }

  if (!session?.isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}
