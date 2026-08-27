import { useEffect, useState } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { Loader } from '@gravity-ui/uikit'
import { useSession } from '../lib/SessionContext'

/**
 * Route guard: redirects a read-only session away from a pure mutation route
 * (`route({ write: true })`) before its form ever renders, mirrored for Flow's
 * own create/edit routes.
 * Sits nested inside `Protected`, so a session is already confirmed
 * authenticated by the time this renders.
 *
 * This is a UX guard against a dead-end form, not itself the security
 * boundary: the real one is each write endpoint's own backend read-only
 * check (the Core-guarded facade). While access state is
 * unknown or failed to (re)load, the form is withheld rather than assumed
 * writable.
 */
export function WriteProtected() {
  const { session, error, refresh } = useSession()
  const [entryRefreshComplete, setEntryRefreshComplete] = useState(false)

  useEffect(() => {
    let active = true
    void refresh().finally(() => {
      if (active) setEntryRefreshComplete(true)
    })
    return () => {
      active = false
    }
  }, [refresh])

  if (!entryRefreshComplete || error || !session) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
        <Loader size="l" />
      </div>
    )
  }

  if (session.isReadOnly) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
