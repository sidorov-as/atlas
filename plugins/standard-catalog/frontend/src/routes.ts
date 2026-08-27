// System/Component/Resource/Team routes — split out of `frontend/src/plugins/core/routes.ts`
// Paths/components are unchanged from core's version, only
// which package declares them moves.
import { route } from '@atlas/plugin-api'
import { ComponentDetailPage } from './pages/ComponentDetailPage'
import { ComponentFormPage } from './pages/ComponentFormPage'
import { ComponentsListPage } from './pages/ComponentsListPage'
import { ResourceDetailPage } from './pages/ResourceDetailPage'
import { ResourceFormPage } from './pages/ResourceFormPage'
import { ResourcesListPage } from './pages/ResourcesListPage'
import { SystemDetailPage } from './pages/SystemDetailPage'
import { SystemFormPage } from './pages/SystemFormPage'
import { SystemsListPage } from './pages/SystemsListPage'
import { TeamDetailPage } from './pages/TeamDetailPage'
import { TeamsListPage } from './pages/TeamsListPage'

export const standardCatalogRoutes = [
  route({ id: 'atlas.standard-catalog.systems.list', path: '/systems', component: SystemsListPage }),
  route({ id: 'atlas.standard-catalog.systems.new', path: '/systems/new', component: SystemFormPage, write: true }),
  route({ id: 'atlas.standard-catalog.systems.detail', path: '/systems/:id', component: SystemDetailPage }),
  route({ id: 'atlas.standard-catalog.systems.edit', path: '/systems/:id/edit', component: SystemFormPage, write: true }),

  route({ id: 'atlas.standard-catalog.components.list', path: '/components', component: ComponentsListPage }),
  route({ id: 'atlas.standard-catalog.components.new', path: '/components/new', component: ComponentFormPage, write: true }),
  route({ id: 'atlas.standard-catalog.components.detail', path: '/components/:id', component: ComponentDetailPage }),
  route({ id: 'atlas.standard-catalog.components.edit', path: '/components/:id/edit', component: ComponentFormPage, write: true }),

  route({ id: 'atlas.standard-catalog.resources.list', path: '/resources', component: ResourcesListPage }),
  route({ id: 'atlas.standard-catalog.resources.new', path: '/resources/new', component: ResourceFormPage, write: true }),
  route({ id: 'atlas.standard-catalog.resources.detail', path: '/resources/:id', component: ResourceDetailPage }),
  route({ id: 'atlas.standard-catalog.resources.edit', path: '/resources/:id/edit', component: ResourceFormPage, write: true }),

  route({ id: 'atlas.standard-catalog.teams.list', path: '/teams', component: TeamsListPage }),
  route({ id: 'atlas.standard-catalog.teams.detail', path: '/teams/:id', component: TeamDetailPage }),
]
