import { ThemeProvider, ToasterComponent, ToasterProvider } from '@gravity-ui/uikit'
import { toaster } from '@gravity-ui/uikit/toaster-singleton'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AdminProtected } from './components/AdminProtected'
import { ContributionBoundary } from './components/ContributionBoundary'
import { Protected } from './components/Protected'
import { WriteProtected } from './components/WriteProtected'
import { SessionProvider } from './lib/SessionContext'
import { composedContributions } from './plugins/composition'
import type { RouteContribution } from '@atlas/plugin-api'

// Routes gated by `AdminProtected` in addition to the session guard every protected
// route already gets — matched by id rather than a generic per-route flag on
// `RouteContribution` (mirrors `Protected.tsx`'s
// nav-item-hiding special case for the same reason: Settings is the only
// admin-gated destination today).
const ADMIN_ONLY_ROUTE_IDS = new Set(['atlas.core.settings'])

/** Isolates one route contribution's render errors so it can't crash the shell or any sibling route (ADR 0020). */
function RouteBoundary({ route }: { route: RouteContribution }) {
  return (
    <ContributionBoundary label="This page">
      <route.component />
    </ContributionBoundary>
  )
}

function App() {
  const publicRoutes = composedContributions.routes.filter((routeContribution) => routeContribution.public)
  const protectedRoutes = composedContributions.routes.filter((routeContribution) => !routeContribution.public)
  const adminOnlyRoutes = protectedRoutes.filter((routeContribution) => ADMIN_ONLY_ROUTE_IDS.has(routeContribution.id))
  // Every plugin's own route list is the inventory (each declares `write: true` on its pure
  // mutation routes) rather than a central id list here.
  const writeOnlyRoutes = protectedRoutes.filter((routeContribution) => routeContribution.write)
  const otherProtectedRoutes = protectedRoutes.filter(
    (routeContribution) => !ADMIN_ONLY_ROUTE_IDS.has(routeContribution.id) && !routeContribution.write,
  )

  return (
    <ThemeProvider theme="system">
      <ToasterProvider toaster={toaster}>
        <ToasterComponent />
        <BrowserRouter>
          <SessionProvider>
            <Routes>
              {publicRoutes.map((routeContribution) => (
                <Route key={routeContribution.id} path={routeContribution.path} element={<RouteBoundary route={routeContribution} />} />
              ))}
              <Route element={<Protected navItems={composedContributions.navItems} globalSearch={composedContributions.globalSearch} />}>
                {otherProtectedRoutes.map((routeContribution) => (
                  <Route key={routeContribution.id} path={routeContribution.path} element={<RouteBoundary route={routeContribution} />} />
                ))}
                <Route element={<AdminProtected />}>
                  {adminOnlyRoutes.map((routeContribution) => (
                    <Route key={routeContribution.id} path={routeContribution.path} element={<RouteBoundary route={routeContribution} />} />
                  ))}
                </Route>
                <Route element={<WriteProtected />}>
                  {writeOnlyRoutes.map((routeContribution) => (
                    <Route key={routeContribution.id} path={routeContribution.path} element={<RouteBoundary route={routeContribution} />} />
                  ))}
                </Route>
              </Route>
            </Routes>
          </SessionProvider>
        </BrowserRouter>
      </ToasterProvider>
    </ThemeProvider>
  )
}

export default App
