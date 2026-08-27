// API's routes — split out of `frontend/plugins/core/routes.ts`.
// Paths/components are unchanged from core's version, only which package declares them moves.
import { route } from '@atlas/plugin-api'
import { ApiDetailPage } from './pages/ApiDetailPage'
import { ApiFormPage } from './pages/ApiFormPage'
import { ApisListPage } from './pages/ApisListPage'
import { EndpointDetailPage } from './pages/EndpointDetailPage'
import { OperationDetailPage } from './pages/OperationDetailPage'

export const apisRoutes = [
  route({ id: 'atlas.apis.apis.list', path: '/apis', component: ApisListPage }),
  route({ id: 'atlas.apis.apis.new', path: '/apis/new', component: ApiFormPage, write: true }),
  route({ id: 'atlas.apis.apis.detail', path: '/apis/:id', component: ApiDetailPage }),
  route({ id: 'atlas.apis.apis.edit', path: '/apis/:id/edit', component: ApiFormPage, write: true }),
  route({ id: 'atlas.apis.apis.endpoint.detail', path: '/apis/:apiId/endpoints/:endpointId', component: EndpointDetailPage }),
  route({ id: 'atlas.apis.apis.operation.detail', path: '/apis/:apiId/operations/:operationId', component: OperationDetailPage }),
]
