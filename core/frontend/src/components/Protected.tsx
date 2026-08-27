import { Outlet } from 'react-router-dom'
import { AppShell } from './AppShell'
import { RequireSession } from './RequireSession'
import { useSession } from '../lib/SessionContext'
import type { ResolvedNavItem } from '@atlas/plugin-api'

// Hidden from non-admins by id rather than a generic nav-item gating flag —
// `NavItemContribution`'s shape stays unchanged (no nav
// sections), and Settings is the only admin-gated destination today
const ADMIN_ONLY_NAV_ITEM_IDS = new Set(['atlas.core.nav.settings'])

/** Session guard + nav shell layout route, shared by every non-`public` route contribution. */
export function Protected({ navItems }: { navItems: readonly ResolvedNavItem[] }) {
  const { session } = useSession()
  const visibleNavItems = session?.isAdmin
    ? navItems
    : navItems.filter((item) => !ADMIN_ONLY_NAV_ITEM_IDS.has(item.id))

  return (
    <RequireSession>
      <AppShell navItems={visibleNavItems}>
        <Outlet />
      </AppShell>
    </RequireSession>
  )
}
