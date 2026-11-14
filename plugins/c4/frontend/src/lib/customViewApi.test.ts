// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from 'frontend/lib/api'
import { componentsApi, groupsApi, resourcesApi, systemsApi, usersApi } from 'frontend/lib/entities'
import { settingsFromBody } from './customView'
import { fieldError, pickerKinds, resolvePickerEntities, searchPickerEntities, viewsApi } from './customViewApi'

vi.mock('frontend/lib/entities', () => {
  const api = () => ({ list: vi.fn(), get: vi.fn() })
  return { systemsApi: api(), componentsApi: api(), resourcesApi: api(), apisApi: api(), groupsApi: api(), usersApi: api() }
})

const page = (...items: unknown[]) => ({ page: { objectList: items } })
const entity = (id: string, kind: string, name: string, spec: object = {}) => ({ id, kind, metadata: { name, title: '' }, spec })

beforeEach(() => vi.clearAllMocks())

describe('pickerKinds', () => {
  const actorKinds = [{ kind: 'group', label: 'Group' }, { kind: 'user', label: 'User' }, { kind: 'bot', label: 'Bot' }]

  it('offers Systems at the systems level, actors only when enabled', () => {
    expect(pickerKinds('systems', [], actorKinds)).toEqual(['system'])
    expect(pickerKinds('systems', ['actor'], actorKinds)).toEqual(['system', 'group', 'user'])
  })

  it('limits the components level to the enabled types', () => {
    expect(pickerKinds('components', ['component', 'api'], actorKinds)).toEqual(['component', 'api'])
  })
})

describe('searchPickerEntities', () => {
  it('merges kinds, shows the System, and never offers a chosen or duplicate entity', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue(page(
      entity('c1', 'Component', 'billing', { system: 'system:payments', type: 'service' }),
      entity('c2', 'Component', 'chosen', { system: 'system:payments' }),
    ) as never)
    vi.mocked(resourcesApi.list).mockResolvedValue(page(
      entity('r1', 'Resource', 'billing-db', { system: null, type: 'database' }),
      entity('c1', 'Resource', 'duplicate'),
    ) as never)
    const results = await searchPickerEntities('bill', ['component', 'resource'], ['c2'])
    expect(results.map((r) => [r.id, r.kind, r.system])).toEqual([
      ['c1', 'component', 'payments'],
      ['r1', 'resource', null],
    ])
    expect(componentsApi.list).toHaveBeenCalledWith({ q: 'bill', pageSize: 8 })
  })

  it('searches actor kinds and shows a user display name', async () => {
    vi.mocked(usersApi.list).mockResolvedValue([{ id: 'u1', kind: 'User', metadata: { name: 'jdoe', title: '' }, spec: { profile: { displayName: 'Jane Doe' } } }] as never)
    vi.mocked(groupsApi.list).mockResolvedValue(page() as never)
    const results = await searchPickerEntities('j', ['group', 'user'], [])
    expect(results).toMatchObject([{ id: 'u1', kind: 'user', name: 'Jane Doe' }])
  })
})

describe('resolvePickerEntities', () => {
  it('finds each id under whichever kind returns it and reports the rest as missing', async () => {
    const notFound = new ApiError(404, null)
    vi.mocked(systemsApi.get).mockImplementation(async (id) => {
      if (id === 's1') return entity('s1', 'System', 'payments') as never
      throw notFound
    })
    vi.mocked(groupsApi.get).mockRejectedValue(notFound)
    vi.mocked(usersApi.get).mockImplementation(async (id) => {
      if (id === 'u1') return entity('u1', 'User', 'jdoe') as never
      throw notFound
    })
    const { found, missing } = await resolvePickerEntities(['s1', 'u1', 'gone'], 'systems', [{ kind: 'group', label: 'Group' }, { kind: 'user', label: 'User' }])
    expect(found.map((e) => e.id)).toEqual(['s1', 'u1'])
    expect(missing).toEqual(['gone'])
  })

  it('propagates non-404 failures instead of treating them as missing', async () => {
    vi.mocked(systemsApi.get).mockRejectedValue(new ApiError(500, null))
    await expect(resolvePickerEntities(['s1'], 'systems', [])).rejects.toBeInstanceOf(ApiError)
  })
})


describe('viewsApi', () => {
  const stored = { id: 'v1', name: 'Billing', description: '', missingEntities: [], createdAt: 't', updatedAt: 't',
    settings: { level: 'systems', selection: 'selected', entities: ['s1'], depth: null, direction: null, entityTypes: null, relationships: 'declared' } }

  function mockFetch(response: unknown, status = 200) {
    const fetchMock = vi.fn().mockResolvedValue(new Response(status === 204 ? null : JSON.stringify(response), { status }))
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  it('lists with the search, page, and sort parameters and maps stored settings', async () => {
    const fetchMock = mockFetch({ count: 1, numPages: 1, perPage: 20, page: { number: 1, objectList: [stored] } })
    const result = await viewsApi.list({ q: 'bill', page: 2, pageSize: 15, sort: '-name' })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/plugins/atlas.c4/views/?q=bill&page=2&page_size=15&sort=-name')
    expect(result.page.objectList[0].settings).toMatchObject({ depth: 1, direction: 'both', entityTypes: ['actor'] })
  })

  it('creates with a JSON body and updates with PUT', async () => {
    const input = { name: 'Billing', description: 'd', settings: settingsFromBody(stored.settings as never) }
    const create = mockFetch(stored, 201)
    await viewsApi.create(input)
    expect(create.mock.calls[0][1]).toMatchObject({ method: 'POST' })
    expect(JSON.parse(create.mock.calls[0][1].body)).toMatchObject({ name: 'Billing', settings: { level: 'systems', entities: ['s1'] } })
    const update = mockFetch(stored)
    await viewsApi.update('v1', input)
    expect(update.mock.calls[0][0]).toBe('/api/plugins/atlas.c4/views/v1/')
    expect(update.mock.calls[0][1]).toMatchObject({ method: 'PUT' })
  })

  it('deletes a view', async () => {
    const fetchMock = mockFetch(null, 204)
    await viewsApi.remove('v1')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'DELETE' })
  })
})

describe('fieldError', () => {
  it('reads the message for a field from a dmr error body', () => {
    const error = new ApiError(400, { detail: [{ msg: 'A view with this name already exists', loc: ['parsed_body', 'name'] }] })
    expect(fieldError(error, 'name')).toBe('A view with this name already exists')
    expect(fieldError(error, 'description')).toBeNull()
    expect(fieldError(new Error('x'), 'name')).toBeNull()
  })
})
