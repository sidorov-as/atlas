import { useState, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AsideHeader, FooterItem, type AsideHeaderItem } from '@gravity-ui/navigation'
import { User } from '@gravity-ui/uikit'
import { ArrowRightFromLine } from '@gravity-ui/icons'
import { useSession } from '../lib/SessionContext'
import { atlasConfig } from '../atlas.config'
import { SKIP_AUTO_START_KEY } from '../pages/LoginPage'
import { ContributionBoundary } from './ContributionBoundary'
import type { GlobalSearchContribution, ResolvedNavItem } from '@atlas/plugin-api'

export function AppShell({
  children,
  navItems,
  globalSearch,
}: {
  children: ReactNode
  navItems: readonly ResolvedNavItem[]
  globalSearch?: GlobalSearchContribution
}) {
  const { session, logout } = useSession()
  const navigate = useNavigate()
  const location = useLocation()
  const [compact, setCompact] = useState(false)

  const menuItems: AsideHeaderItem[] = navItems.map((item) => ({
    id: item.id,
    title: item.title,
    icon: item.icon,
    href: item.resolvedPath,
    current: location.pathname === item.resolvedPath || location.pathname.startsWith(`${item.resolvedPath}/`),
    onItemClick: (_menuItem, _collapsed, event) => {
      event.preventDefault()
      navigate(item.resolvedPath)
    },
  }))

  return (
    <AsideHeader
      compact={compact}
      onChangeCompact={setCompact}
      logo={{
        text: () => (
          <div style={{paddingLeft: 6}}>
            <div style={{ fontSize: 20 }}>{atlasConfig.title}</div>
            <div className="app-shell-logo-subtitle">software catalog</div>
          </div>
        ),
        iconSrc: atlasConfig.logo,
        iconSize: 50,
        className: 'app-shell-logo',
        onClick: () => navigate('/'),
      }}
      menuItems={menuItems}
      renderContent={() => (
        <main style={{ padding: 24, paddingLeft: 60, paddingTop: 60 }}>
          {globalSearch && (
            <div className="app-shell-search" style={{ marginBottom: 16 }}>
              <ContributionBoundary label="Search">
                <globalSearch.component />
              </ContributionBoundary>
            </div>
          )}
          {children}
        </main>
      )}
      renderFooter={({ compact: isCompact }) => {
        const username = session?.user?.username ?? ''
        return (
          <>
            <div style={{ padding: '6px 12px' }}>
              <User avatar={{ text: username }} name={isCompact ? undefined : username} size="s" />
            </div>
            <FooterItem
              id="logout"
              title="Log out"
              icon={ArrowRightFromLine}
              onItemClick={() => {
                // Set before the awaited DELETE below, so it's already in place no
                // matter which redirect to /login reaches the router first — see
                // SKIP_AUTO_START_KEY.
                window.sessionStorage.setItem(SKIP_AUTO_START_KEY, '1')
                void logout()
              }}
            />
          </>
        )
      }}
    />
  )
}
