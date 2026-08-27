// Thin REST clients for `atlas_plugin_apis`'s cross-API Endpoint/Operation
// search,
// backing the Flow "Add Step" Query/Event picker (`FlowStepModal.tsx`).
//
// `@atlas/plugin-flows` cannot depend on `@atlas/plugin-apis` as an npm
// package (`core/frontend/src/plugins/importBoundary.test.ts` forbids a
// first-party plugin importing another's directly) — REST is the only legal
// cross-plugin channel on the frontend, symmetric to `.extension_points`
// being the only legal one on the backend. So this module keeps its own,
// deliberately minimal read shapes (just what the picker renders) rather
// than importing `@atlas/plugin-apis`'s own `Endpoint`/`Operation` types.
//
// `summary` is already
// present in the backend's `EndpointOut`/`OperationOut` response body —
// `EndpointSearchResultOut`/`OperationSearchResultOut` embed those whole —
// this just widens the frontend read shape to pick it up, no backend change.
//
// Both search endpoints are offset-paginated, mirroring `EndpointServicesQuery`/
// `OperationServicesQuery`'s existing `page`/`page_size` convention — this
// module's `search` functions take a `page` and return the app-wide
// `Paginated<T>` shape instead of a flat capped array.
import { apiJson } from 'frontend/lib/api'
import type { Paginated } from 'frontend/lib/types'

export interface ApiSummary {
  ref: string
  name: string
  title: string
}

export interface EndpointSearchResult {
  endpoint: {
    id: string
    method: string
    path: string
    summary: string
  }
  api: ApiSummary
}

export interface OperationSearchResult {
  operation: {
    id: string
    channelAddress: string
    direction: string
    summary: string
  }
  api: ApiSummary
}

function toSearchQuery(search: string, page: number): string {
  const params = new URLSearchParams()
  if (search) params.set('search', search)
  if (page) params.set('page', String(page))
  const query = params.toString()
  return query ? `?${query}` : ''
}

export const endpointsApi = {
  search: (search: string, page = 1) =>
    apiJson<Paginated<EndpointSearchResult>>(`/api/apis/endpoints/search/${toSearchQuery(search, page)}`),
}

export const operationsApi = {
  search: (search: string, page = 1) =>
    apiJson<Paginated<OperationSearchResult>>(`/api/apis/operations/search/${toSearchQuery(search, page)}`),
}
