// Thin client for `atlas.search`'s HTTP contract (`/api/plugins/atlas.search/`).
import { ApiError, apiJson } from 'frontend/lib/api'

const BASE = '/api/plugins/atlas.search'

export interface SearchSnippet {
  text: string
  /** `[start, end)` offsets into `text` in UTF-16 code units, the unit of JS string indexes. */
  matches: [number, number][]
}

export interface SearchResult {
  id: string
  kind: string
  kindLabel: string
  title: string
  link: string
  snippet: SearchSnippet | null
}

/** Authorized matches of the query for one kind, regardless of the kind filter. */
export interface KindCount {
  kind: string
  kindLabel: string
  count: number
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
  /** Per-kind counts for the whole query; present because the client always asks for them. */
  facets?: KindCount[] | null
}

export interface SearchStatus {
  ok: boolean
  engineHealthy: boolean
  pendingCount: number
  oldestPendingAgeSeconds: number | null
}

/** The search service reported itself unavailable (HTTP 503), as opposed to "no results". */
export class SearchUnavailableError extends Error {
  constructor() {
    super('Search is unavailable')
    this.name = 'SearchUnavailableError'
  }
}

export const searchApi = {
  /** `kind` narrows the results to one kind; the per-kind `facets` in the response always cover every kind. */
  async search(query: string, { kind, signal }: { kind?: string | null; signal?: AbortSignal } = {}): Promise<SearchResponse> {
    const params = new URLSearchParams({ q: query, facets: 'true' })
    if (kind) params.set('kinds', kind)
    try {
      return await apiJson<SearchResponse>(`${BASE}/search/?${params}`, { signal })
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) throw new SearchUnavailableError()
      throw err
    }
  },
  status: (signal?: AbortSignal) => apiJson<SearchStatus>(`${BASE}/status/`, { signal }),
}
