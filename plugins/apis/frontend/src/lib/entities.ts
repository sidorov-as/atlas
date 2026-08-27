// Typed wrappers around the read-only Endpoint API (no
// create/update endpoints exist) — follows `frontend/lib/entities`'
// conventions (list/get functions, a `toQuery` query-string builder).
import { apiJson } from 'frontend/lib/api'
import type { Paginated } from 'frontend/lib/types'
import type {
  Endpoint,
  EndpointConsumers,
  EndpointListFilters,
  EndpointService,
  EndpointServiceLink,
  Operation,
  OperationConsumers,
  OperationListFilters,
  OperationRole,
  OperationService,
  OperationServiceLink,
} from './types'

function toEndpointQuery(filters: EndpointListFilters = {}): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== '') params.set(key, String(value))
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export const endpointsApi = {
  list: (apiId: string, filters?: EndpointListFilters) =>
    apiJson<Endpoint[]>(`/api/apis/${apiId}/endpoints/${toEndpointQuery(filters)}`),
  get: (apiId: string, endpointId: string) =>
    apiJson<Endpoint>(`/api/apis/${apiId}/endpoints/${endpointId}/`),
}

// --- Service <-> Endpoint dependency --------------

export interface EndpointServicesFilters {
  search?: string
  teamId?: string
  sort?: 'service' | 'team'
  order?: 'asc' | 'desc'
  page?: number
  pageSize?: number
}

function toEndpointServicesQuery(filters: EndpointServicesFilters = {}): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === '') continue
    const paramKey = key === 'teamId' ? 'team_id' : key === 'pageSize' ? 'page_size' : key
    params.set(paramKey, String(value))
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export const endpointServicesApi = {
  list: (endpointId: string, filters?: EndpointServicesFilters) =>
    apiJson<Paginated<EndpointService>>(`/api/endpoints/${endpointId}/services/${toEndpointServicesQuery(filters)}`),
  link: (endpointId: string, serviceId: string) =>
    apiJson<EndpointServiceLink>(`/api/endpoints/${endpointId}/services/`, {
      method: 'POST',
      body: JSON.stringify({ serviceId }),
    }),
  unlink: (endpointId: string, serviceId: string) =>
    apiJson<void>(`/api/endpoints/${endpointId}/services/${serviceId}/`, { method: 'DELETE' }),
  consumers: (endpointId: string) =>
    apiJson<EndpointConsumers>(`/api/endpoints/${endpointId}/consumers/`),
}

// --- Operation -
// Typed wrappers around the read-only Operation API (no
// create/update endpoints exist), following the same conventions as
// `endpointsApi`/`endpointServicesApi` above.

function toOperationQuery(filters: OperationListFilters = {}): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== '') params.set(key, String(value))
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export const operationsApi = {
  list: (apiId: string, filters?: OperationListFilters) =>
    apiJson<Operation[]>(`/api/apis/${apiId}/operations/${toOperationQuery(filters)}`),
  get: (apiId: string, operationId: string) =>
    apiJson<Operation>(`/api/apis/${apiId}/operations/${operationId}/`),
}

// --- Service <-> Operation dependency -------------

export interface OperationServicesFilters {
  search?: string
  teamId?: string
  role?: OperationRole
  sort?: 'service' | 'team'
  order?: 'asc' | 'desc'
  page?: number
  pageSize?: number
}

function toOperationServicesQuery(filters: OperationServicesFilters = {}): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === '') continue
    const paramKey = key === 'teamId' ? 'team_id' : key === 'pageSize' ? 'page_size' : key
    params.set(paramKey, String(value))
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export const operationServicesApi = {
  list: (operationId: string, filters?: OperationServicesFilters) =>
    apiJson<Paginated<OperationService>>(`/api/operations/${operationId}/services/${toOperationServicesQuery(filters)}`),
  link: (operationId: string, serviceId: string, role: OperationRole) =>
    apiJson<OperationServiceLink>(`/api/operations/${operationId}/services/`, {
      method: 'POST',
      body: JSON.stringify({ serviceId, role }),
    }),
  unlink: (operationId: string, serviceId: string, role: OperationRole) =>
    apiJson<void>(`/api/operations/${operationId}/services/${serviceId}/?role=${role}`, { method: 'DELETE' }),
  consumers: (operationId: string) =>
    apiJson<OperationConsumers>(`/api/operations/${operationId}/consumers/`),
}
