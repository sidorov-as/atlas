import { Navigate, Outlet } from 'react-router-dom'
import { useSession } from '../lib/SessionContext'

/**
 * Route guard: redirects a non-admin away from an admin-only route
 * Sits nested inside `Protected` — a session is
 * already confirmed authenticated by the time this renders, so it only
 * needs to check `isAdmin`.
 *
 * This is a UX guard against a dead-end UI, not itself the security
 * boundary: the real one is each Settings-owned write endpoint's own
 * `is_superuser` check server-side (two independent
 * layers, not one).
 */
export function AdminProtected() {
  const { session } = useSession()

  if (!session?.isAdmin) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
