// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { ApiError } from 'frontend/lib/api'
import { apisApi, componentsApi, groupsApi, resourcesApi, systemsApi, usersApi } from 'frontend/lib/entities'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ViewEditorPage } from './ViewEditorPage'

vi.mock('frontend/lib/entities', () => {
  const api = () => ({ list: vi.fn(), get: vi.fn() })
  return { systemsApi: api(), componentsApi: api(), resourcesApi: api(), apisApi: api(), groupsApi: api(), usersApi: api() }
})

class ResizeObserverStub {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}
globalThis.ResizeObserver = ResizeObserverStub

// jsdom has no matchMedia; Gravity UI's Dialog needs it.
window.matchMedia = window.matchMedia || (((query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: () => {},
  removeListener: () => {},
  addEventListener: () => {},
  removeEventListener: () => {},
  dispatchEvent: () => false,
})) as unknown as typeof window.matchMedia)

const SYSTEM = '11111111-1111-4111-8111-111111111111'
const COMPONENT = '22222222-2222-4222-8222-222222222222'
const GONE = '33333333-3333-4333-8333-333333333333'
const VIEW_ID = '44444444-4444-4444-8444-444444444444'

const entity = (id: string, kind: string, name: string, spec: object = {}) => ({ id, kind, metadata: { name, title: '' }, spec })
const page = (...items: unknown[]) => ({ page: { objectList: items } })

const fetchMock = vi.fn()
let created = 0

const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const svg = () => new Response('<svg />', { status: 200 })

const savedView = (settings: object, extra: object = {}) => ({
  id: VIEW_ID, name: 'Billing', description: 'About', missingEntities: [], createdAt: 't', updatedAt: 't', settings, ...extra,
})
const SYSTEM_SETTINGS = { level: 'systems', selection: 'selected', entities: [SYSTEM], entityTypes: ['actor'], relationships: 'declared' }
const COMPONENT_SETTINGS = { level: 'components', selection: 'neighborhood', entities: [COMPONENT], depth: 2, direction: 'both', entityTypes: ['component', 'resource', 'api', 'actor'], relationships: 'declared' }

type Handlers = {
  preview?: (body: Record<string, unknown>) => Response
  view?: unknown
  save?: (method: string, body: Record<string, unknown>) => Response
}

function serve({ preview = () => svg(), view, save }: Handlers = {}) {
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    const target = String(url)
    const method = init?.method ?? 'GET'
    const body = typeof init?.body === 'string' ? (JSON.parse(init.body) as Record<string, unknown>) : {}
    if (target.includes('actor-kinds')) return json(200, { items: [{ kind: 'group', label: 'Group' }, { kind: 'user', label: 'User' }] })
    if (target.includes('/diagrams/custom/')) return preview(body)
    if (target.includes('/views/')) {
      if (method === 'GET') return view ? json(200, view) : json(404, { detail: [{ msg: 'View not found', type: 'not_found' }] })
      return save ? save(method, body) : json(method === 'POST' ? 201 : 200, savedView(body.settings as object, { name: body.name }))
    }
    return json(404, {})
  })
}

const previews = () => fetchMock.mock.calls.filter(([url]) => String(url).includes('/diagrams/custom/'))
const saves = () => fetchMock.mock.calls.filter(([url, init]) => String(url).includes('/views/') && (init?.method ?? 'GET') !== 'GET')
const previewBody = (index: number) => JSON.parse((previews()[index][1] as RequestInit).body as string)

function Probe() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname}</output>
}

function renderEditor(url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <ThemeProvider theme="light">
        <Routes>
          <Route path="/system-map/views/new" element={<ViewEditorPage />} />
          <Route path="/system-map/views/:id/edit" element={<ViewEditorPage />} />
          <Route path="*" element={<Probe />} />
        </Routes>
      </ThemeProvider>
    </MemoryRouter>,
  )
}

/** The editor's own Cancel, not a dialog's. */
function cancelButton() {
  const buttons = screen.getAllByRole('button', { name: 'Cancel' })
  return buttons.find((button) => !button.closest('[role="dialog"]')) ?? buttons[0]
}

async function addEntity(query: string, label: string) {
  const search = await screen.findByRole('textbox', { name: 'Search entities' })
  fireEvent.focus(search)
  fireEvent.change(search, { target: { value: query } })
  fireEvent.click(await screen.findByText(label))
}

beforeEach(() => {
  created = 0
  vi.stubGlobal('fetch', fetchMock)
  URL.createObjectURL = vi.fn(() => `blob:${++created}`)
  URL.revokeObjectURL = vi.fn()
  const notFound = new ApiError(404, null)
  vi.mocked(systemsApi.get).mockImplementation(async (id) => {
    if (id === SYSTEM) return entity(SYSTEM, 'System', 'Payments') as never
    throw notFound
  })
  vi.mocked(componentsApi.get).mockImplementation(async (id) => {
    if (id === COMPONENT) return entity(COMPONENT, 'Component', 'Billing API', { system: 'system:payments', type: 'service' }) as never
    throw notFound
  })
  for (const api of [resourcesApi, apisApi, groupsApi, usersApi]) vi.mocked(api.get).mockRejectedValue(notFound)
  vi.mocked(systemsApi.list).mockResolvedValue(page(entity(SYSTEM, 'System', 'Payments')) as never)
  vi.mocked(componentsApi.list).mockResolvedValue(page(entity(COMPONENT, 'Component', 'Billing API', { system: 'system:payments', type: 'service' })) as never)
  for (const api of [resourcesApi, apisApi, groupsApi]) vi.mocked(api.list).mockResolvedValue(page() as never)
  vi.mocked(usersApi.list).mockResolvedValue([] as never)
})

afterEach(() => {
  cleanup()
  fetchMock.mockReset()
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('ViewEditorPage: new view', () => {
  it('starts empty: nothing is fetched and neither Apply nor Save is possible', async () => {
    serve()
    renderEditor('/system-map/views/new')
    expect(await screen.findByText('Select at least one entity to build a view.')).toBeDefined()
    expect(screen.getByRole('heading', { name: 'Create view' })).toBeDefined()
    expect((screen.getByRole('button', { name: 'Apply view' }) as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: 'Save' }) as HTMLButtonElement).disabled).toBe(true)
    expect(screen.queryByRole('button', { name: /Copy link/ })).toBeNull()
    expect(previews()).toHaveLength(0)
  })

  it('Apply posts the draft as a JSON body and stores nothing', async () => {
    serve()
    renderEditor('/system-map/views/new')
    await addEntity('pay', 'Payments')
    fireEvent.click(screen.getByRole('button', { name: 'Apply view' }))
    await screen.findByAltText('View preview')
    expect(previews()).toHaveLength(1)
    const [url, init] = previews()[0]
    expect(String(url)).not.toContain('entity')
    expect((init as RequestInit).method).toBe('POST')
    expect(previewBody(0)).toMatchObject({ level: 'systems', selection: 'selected', entities: [SYSTEM] })
    expect(previewBody(0)).not.toHaveProperty('depth')
    expect(saves()).toHaveLength(0)
  })

  it('does not fetch while editing, shows the unapplied notice, and Reset changes only the draft', async () => {
    serve({ view: savedView(COMPONENT_SETTINGS) })
    renderEditor(`/system-map/views/${VIEW_ID}/edit`)
    await screen.findByAltText('View preview')
    fireEvent.change(await screen.findByRole('spinbutton', { name: 'Depth' }), { target: { value: '4' } })
    expect(screen.getByText('Unapplied changes. Apply your changes to update the diagram.')).toBeDefined()
    expect(previews()).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: 'Reset' }))
    expect((screen.getByRole('spinbutton', { name: 'Depth' }) as HTMLInputElement).value).toBe('2')
    expect(screen.queryByText(/Unapplied changes/)).toBeNull()
    expect(previews()).toHaveLength(1)
    expect(saves()).toHaveLength(0)
  })

  it('Save stores the draft (without applying it) and opens the view', async () => {
    serve()
    renderEditor('/system-map/views/new')
    await addEntity('pay', 'Payments')
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: 'Billing' } })
    fireEvent.change(screen.getByRole('textbox', { name: 'Description' }), { target: { value: 'About billing' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe(`/system-map/views/${VIEW_ID}`))
    expect(previews()).toHaveLength(0)
    const [url, init] = saves()[0]
    expect(String(url)).toBe('/api/plugins/atlas.c4/views/')
    expect((init as RequestInit).method).toBe('POST')
    expect(JSON.parse((init as RequestInit).body as string)).toMatchObject({
      name: 'Billing', description: 'About billing', settings: { level: 'systems', entities: [SYSTEM] },
    })
  })

  it('shows a duplicate-name error on the Name field and stays on the page', async () => {
    serve({ save: () => json(400, { detail: [{ msg: 'A view with this name already exists', loc: ['parsed_body', 'name'], type: 'value_error' }] }) })
    renderEditor('/system-map/views/new')
    await addEntity('pay', 'Payments')
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: 'Billing' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('A view with this name already exists')).toBeDefined()
    expect(screen.getByRole('heading', { name: 'Create view' })).toBeDefined()
  })

  it('requires a name to save', async () => {
    serve()
    renderEditor('/system-map/views/new')
    await addEntity('pay', 'Payments')
    expect((screen.getByRole('button', { name: 'Save' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: '  ' } })
    expect((screen.getByRole('button', { name: 'Save' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: 'Billing' } })
    expect((screen.getByRole('button', { name: 'Save' }) as HTMLButtonElement).disabled).toBe(false)
  })

  it('asks before leaving with unsaved changes, and lets the user stay or leave', async () => {
    serve()
    renderEditor('/system-map/views/new')
    await addEntity('pay', 'Payments')
    fireEvent.click(cancelButton())
    expect(await screen.findByText('Discard changes?')).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: 'Stay' }))
    await waitFor(() => expect(screen.queryByText('Discard changes?')).toBeNull())
    expect(screen.getByRole('heading', { name: 'Create view' })).toBeDefined()
    fireEvent.click(cancelButton())
    fireEvent.click(await screen.findByRole('button', { name: 'Leave' }))
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/system-map'))
  })

  it('leaves without asking when nothing changed', async () => {
    serve()
    renderEditor('/system-map/views/new')
    await screen.findByText('Select at least one entity to build a view.')
    fireEvent.click(cancelButton())
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/system-map'))
    expect(screen.queryByText('Discard changes?')).toBeNull()
  })

  it('collapses and expands the View settings panel', async () => {
    serve()
    renderEditor('/system-map/views/new')
    await screen.findByRole('form', { name: 'View settings' })
    fireEvent.click(screen.getByRole('button', { name: 'Hide view settings' }))
    expect(screen.queryByRole('form', { name: 'View settings' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Show view settings' }))
    expect(screen.getByRole('form', { name: 'View settings' })).toBeDefined()
  })

  it('clears incompatible entities when the level changes and keeps the previous diagram', async () => {
    serve({ view: savedView(COMPONENT_SETTINGS) })
    renderEditor(`/system-map/views/${VIEW_ID}/edit`)
    await screen.findByAltText('View preview')
    await screen.findByRole('button', { name: 'Remove Billing API' })
    fireEvent.click(screen.getByRole('radio', { name: 'Systems' }))
    expect(screen.getByText('Selection cleared for the new level')).toBeDefined()
    expect(screen.queryByRole('button', { name: 'Remove Billing API' })).toBeNull()
    expect(screen.getByAltText('View preview')).toBeDefined()
  })

  it('blocks disabling a type with chosen entities in Selected mode', async () => {
    serve({ view: savedView({ ...COMPONENT_SETTINGS, selection: 'selected' }) })
    renderEditor(`/system-map/views/${VIEW_ID}/edit`)
    await screen.findByAltText('View preview')
    const components = (await screen.findByRole('checkbox', { name: 'Components' })) as HTMLInputElement
    fireEvent.click(components)
    expect(components.checked).toBe(true)
    expect(screen.getByText('Remove selected entities of this type first')).toBeDefined()
  })

  it('shows kind and System in picker results and never offers a chosen entity again', async () => {
    serve({ view: savedView({ ...COMPONENT_SETTINGS, selection: 'selected' }) })
    renderEditor(`/system-map/views/${VIEW_ID}/edit`)
    await screen.findByAltText('View preview')
    const search = screen.getByRole('textbox', { name: 'Search entities' })
    fireEvent.focus(search)
    await waitFor(() => expect(componentsApi.list).toHaveBeenCalled())
    const results = await screen.findByRole('listbox')
    await waitFor(() => expect(within(results).queryAllByText('Billing API')).toHaveLength(0))
  })
})

describe('ViewEditorPage: failures and stale responses', () => {
  it('keeps the previous preview when a later Apply fails and states the limit and count', async () => {
    let call = 0
    serve({
      view: savedView(COMPONENT_SETTINGS),
      preview: () => (++call === 1 ? svg() : json(422, { detail: [{ msg: 'too many', type: 'node_limit_exceeded', limit: 50, count: 72 }] })),
    })
    renderEditor(`/system-map/views/${VIEW_ID}/edit`)
    await screen.findByAltText('View preview')
    fireEvent.change(await screen.findByRole('spinbutton', { name: 'Depth' }), { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Apply view' }))
    expect(await screen.findByText(/72 nodes but the limit is 50/)).toBeDefined()
    expect(screen.getByText(/new settings were not applied/)).toBeDefined()
    expect(screen.getByAltText('View preview')).toBeDefined()
    expect(screen.queryByRole('button', { name: 'Retry' })).toBeNull()
  })

  it('offers Retry for render failures', async () => {
    let call = 0
    serve({ view: savedView(SYSTEM_SETTINGS), preview: () => (++call === 1 ? json(500, { detail: [{ msg: 'Unable to render diagram', type: 'value_error' }] }) : svg()) })
    renderEditor(`/system-map/views/${VIEW_ID}/edit`)
    fireEvent.click(await screen.findByRole('button', { name: 'Retry' }))
    expect(await screen.findByAltText('View preview')).toBeDefined()
    expect(previews()).toHaveLength(2)
  })

  it('disables Apply while a preview is loading and shows the response once it arrives', async () => {
    const resolvers: Array<(response: Response) => void> = []
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      const target = String(url)
      if (target.includes('actor-kinds')) return json(200, { items: [] })
      if (target.includes('/diagrams/custom/')) return new Promise<Response>((resolve) => resolvers.push(resolve))
      if (target.includes('/views/') && (init?.method ?? 'GET') === 'GET') return json(200, savedView(COMPONENT_SETTINGS))
      return json(404, {})
    })
    renderEditor(`/system-map/views/${VIEW_ID}/edit`)
    await waitFor(() => expect(resolvers).toHaveLength(1))
    await waitFor(() => expect((screen.getByRole('button', { name: 'Apply view' }) as HTMLButtonElement).disabled).toBe(true))
    resolvers[0](svg())
    expect(await screen.findByAltText('View preview')).toBeDefined()
    await waitFor(() => expect((screen.getByRole('button', { name: 'Apply view' }) as HTMLButtonElement).disabled).toBe(false))
  })

  it('lists a removed entity of a saved view with a way to remove it, and saving needs that first', async () => {
    serve({ view: savedView({ ...SYSTEM_SETTINGS, entities: [GONE] }, { missingEntities: [GONE] }) })
    renderEditor(`/system-map/views/${VIEW_ID}/edit`)
    expect(await screen.findByText('Entity not found')).toBeDefined()
    expect(previews()).toHaveLength(0)
    expect((screen.getByRole('button', { name: 'Save' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: `Remove unknown entity ${GONE}` }))
    expect(screen.queryByText('Entity not found')).toBeNull()
  })

  it('reports a view that does not exist', async () => {
    serve()
    renderEditor(`/system-map/views/${VIEW_ID}/edit`)
    expect(await screen.findByText('View not found')).toBeDefined()
  })

  it('saves an edited view with PUT', async () => {
    serve({ view: savedView(SYSTEM_SETTINGS) })
    renderEditor(`/system-map/views/${VIEW_ID}/edit`)
    await screen.findByAltText('View preview')
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: 'Billing v2' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(saves()).toHaveLength(1))
    expect(String(saves()[0][0])).toBe(`/api/plugins/atlas.c4/views/${VIEW_ID}/`)
    expect((saves()[0][1] as RequestInit).method).toBe('PUT')
  })
})

describe('ViewEditorPage: "Open in view builder" prefill', () => {
  it('derives the Systems level from a System root, applies the defaults, and renders immediately', async () => {
    serve()
    renderEditor(`/system-map/views/new?root=${SYSTEM}`)
    await screen.findByAltText('View preview')
    expect(previewBody(0)).toMatchObject({ level: 'systems', selection: 'neighborhood', entities: [SYSTEM], depth: 1, direction: 'both', relationships: 'declared', entityTypes: ['actor'] })
    expect(screen.getByRole('heading', { name: 'View' })).toBeDefined()
  })

  it('derives the Components level from a Component root with every type enabled', async () => {
    serve()
    renderEditor(`/system-map/views/new?root=${COMPONENT}`)
    await screen.findByAltText('View preview')
    expect(previewBody(0)).toMatchObject({ level: 'components', entityTypes: ['component', 'resource', 'api', 'actor'] })
  })

  it('does not ask before leaving a prefilled but untouched editor', async () => {
    serve()
    renderEditor(`/system-map/views/new?root=${SYSTEM}`)
    await screen.findByAltText('View preview')
    fireEvent.click(cancelButton())
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/system-map'))
  })

  it('tells the user about an unknown root and starts empty', async () => {
    serve()
    renderEditor(`/system-map/views/new?root=${GONE}`)
    expect(await screen.findByText(/entity in this link was not found/i)).toBeDefined()
    expect(previews()).toHaveLength(0)
  })
})
