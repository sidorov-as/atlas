// `atlas.c4`'s own nav destination for the System Map — replaces the former `homeWidget` contribution.
// Positioned after "APIs" purely by plugin order in
// `distributions/default/manifest.yaml` (`... apis → c4 ...`), no manifest
// change needed.
import { Hierarchy } from '@gravity-ui/icons'
import { navItem, route, routeRef } from '@atlas/plugin-api'
import { NEW_VIEW_PATH, SYSTEM_MAP_PATH } from './lib/customView'
import { SystemMapPage } from './pages/SystemMapPage'
import { ViewDetailPage } from './pages/ViewDetailPage'
import { ViewEditorPage } from './pages/ViewEditorPage'

export const c4Routes = [
  route({ id: 'atlas.c4.system-map', path: SYSTEM_MAP_PATH, component: SystemMapPage }),
  route({ id: 'atlas.c4.views.new', path: NEW_VIEW_PATH, component: ViewEditorPage, write: true }),
  route({ id: 'atlas.c4.views.detail', path: `${SYSTEM_MAP_PATH}/views/:id`, component: ViewDetailPage }),
  route({ id: 'atlas.c4.views.edit', path: `${SYSTEM_MAP_PATH}/views/:id/edit`, component: ViewEditorPage, write: true }),
]

export const c4NavItems = [
  navItem({ id: 'atlas.c4.nav.system-map', title: 'System Map', icon: Hierarchy, route: routeRef('atlas.c4.system-map') }),
]
