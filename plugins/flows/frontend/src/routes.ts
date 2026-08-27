// Flow's routes — split out of `frontend/plugins/core/routes.ts`.
// Paths/components are unchanged from core's version, only which package declares them moves.
import { route } from '@atlas/plugin-api'
import { FlowDetailPage } from './pages/FlowDetailPage'
import { FlowFormPage } from './pages/FlowFormPage'
import { FlowsListPage } from './pages/FlowsListPage'

export const flowsRoutes = [
  route({ id: 'atlas.flows.flows.list', path: '/flows', component: FlowsListPage }),
  route({ id: 'atlas.flows.flows.new', path: '/flows/new', component: FlowFormPage, write: true }),
  route({ id: 'atlas.flows.flows.detail', path: '/flows/:id', component: FlowDetailPage }),
  route({ id: 'atlas.flows.flows.edit', path: '/flows/:id/edit', component: FlowFormPage, write: true }),
]
