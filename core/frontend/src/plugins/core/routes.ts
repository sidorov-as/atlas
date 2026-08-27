// Every route App.tsx used to declare as a literal <Route>, now as `route(...)` contributions
// Paths/components are unchanged from the previous
// literal <Routes> tree — only how they're assembled moves from static JSX to composition.
// Bare page components: App.tsx applies the session-guard + nav-shell layout to every
// non-`public` route itself (a react-router layout route), so this module — and anything a
// consumer of `entityDetailTabs` pulls in transitively — never needs to import AppShell.
//
// System/Component/Resource/Team routes moved to `@atlas/plugin-standard-catalog`
// APIs' to `@atlas/plugin-apis`,
// Flows' to `@atlas/plugin-flows` — what's left here (Login/Home/
// Settings) is core-owned (Login is Authentication Core's concern; Settings is a
// cross-cutting concern).
import { route } from '@atlas/plugin-api'
import { HomePage } from '../../pages/HomePage'
import { LoginPage } from '../../pages/LoginPage'
import { SettingsLayout } from '../../pages/SettingsLayout'

export const coreRoutes = [
  route({ id: 'atlas.core.login', path: '/login', component: LoginPage, public: true }),
  route({ id: 'atlas.core.home', path: '/', component: HomePage }),

  // Nested Settings area — `SettingsLayout` owns its own
  // internal `<Routes>` for `/settings/home` and `/settings/tags`, with `/settings`
  // redirecting to `/settings/home`. Gated by `AdminProtected` in `App.tsx` (matched
  // by this route's id), on top of the session guard every protected route already gets.
  route({ id: 'atlas.core.settings', path: '/settings/*', component: SettingsLayout }),
]
