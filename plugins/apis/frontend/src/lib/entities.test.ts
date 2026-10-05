import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiJson } from 'frontend/lib/api'
import { endpointServicesApi, operationServicesApi } from './entities'

vi.mock('frontend/lib/api', () => ({ apiJson: vi.fn() }))

afterEach(() => vi.clearAllMocks())

function page<T>(number: number, numPages: number, objectList: T[]) {
  return { count: 120, numPages, perPage: 100, page: { number, objectList } }
}

describe('already-linked lookups', () => {
  it('collects every Service id across all pages for an Endpoint', async () => {
    vi.mocked(apiJson)
      .mockResolvedValueOnce(page(1, 2, Array.from({ length: 100 }, (_, i) => ({ service: { id: `s-${i}` } }))))
      .mockResolvedValueOnce(page(2, 2, [{ service: { id: 'last' } }]))

    const ids = await endpointServicesApi.linkedServiceIds('endpoint-1')

    expect(ids).toHaveLength(101)
    expect(ids).toContain('last')
    expect(vi.mocked(apiJson).mock.calls.map((call) => call[0])).toEqual([
      '/api/endpoints/endpoint-1/services/?page=1&page_size=100',
      '/api/endpoints/endpoint-1/services/?page=2&page_size=100',
    ])
  })

  it('collects every service:role pair across all pages for an Operation', async () => {
    vi.mocked(apiJson)
      .mockResolvedValueOnce(page(1, 2, [{ service: { id: 'a' }, role: 'publisher' }]))
      .mockResolvedValueOnce(page(2, 2, [{ service: { id: 'b' }, role: 'subscriber' }]))

    expect(await operationServicesApi.linkedServiceRolePairs('op-1')).toEqual(['a:publisher', 'b:subscriber'])
  })
})

describe('consumers queries', () => {
  it('leaves the URL unchanged without grouping parameters', async () => {
    vi.mocked(apiJson).mockResolvedValue({})
    await endpointServicesApi.consumers('e-1', { search: 'pay', pageSize: 50 })
    expect(vi.mocked(apiJson).mock.calls[0][0]).toBe('/api/endpoints/e-1/consumers/?page_size=50&search=pay')
  })

  it('sends group_by, group_id and role', async () => {
    vi.mocked(apiJson).mockResolvedValue({})
    await operationServicesApi.consumers('o-1', { groupBy: 'team', groupId: 'g-1', role: 'subscriber' })
    expect(vi.mocked(apiJson).mock.calls[0][0]).toBe('/api/operations/o-1/consumers/?group_by=team&group_id=g-1&role=subscriber')
  })
})
