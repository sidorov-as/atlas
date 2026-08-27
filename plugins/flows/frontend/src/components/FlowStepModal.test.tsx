// @vitest-environment jsdom
import type { ComponentProps } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FlowStepModal } from './FlowStepModal'
import { FlowEntityCatalogProvider } from '../lib/flowEntityCatalog'
import type { FlowStep } from '../lib/flowLayout'

// jsdom has no matchMedia/ResizeObserver; Gravity UI's Dialog/Select need
// them (same stubs as `LinkServiceDialog.test.tsx`/`EndpointDetailPage.test.tsx`).
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)
vi.stubGlobal('matchMedia', (query: string) => ({
  matches: false, media: query, onchange: null,
  addListener: () => {}, removeListener: () => {},
  addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
}))

// `FlowEntityCatalogProvider` fetches every entity_ref-backed kind
// via `entities.ts`'s API clients on mount — stubbed here to an empty,
// already-loaded catalog so the modal renders synchronously without a real
// network call, the same approach `FlowNodes.test.tsx` uses for this module.
const { flowsApiList, flowsApiGet } = vi.hoisted(() => ({
  flowsApiList: vi.fn().mockResolvedValue({
    count: 1,
    numPages: 1,
    perPage: 20,
    page: { number: 1, objectList: [{ id: 7, system: 'system:s', name: 'Checkout', description: 'Cart to payment', documentation: '', steps: [], autolayoutEnabled: true, layoutDirection: 'LAYOUT_LEFT_RIGHT', layoutEngine: 'elk' }] },
  }),
  flowsApiGet: vi.fn().mockRejectedValue(new Error('not found')),
}))

vi.mock('frontend/lib/entities', () => ({
  componentsApi: { list: vi.fn().mockResolvedValue({ numPages: 1, page: { objectList: [] } }) },
  resourcesApi: { list: vi.fn().mockResolvedValue({ numPages: 1, page: { objectList: [] } }) },
  apisApi: { list: vi.fn().mockResolvedValue({ numPages: 1, page: { objectList: [] } }) },
  systemsApi: { list: vi.fn().mockResolvedValue({ numPages: 1, page: { objectList: [] } }) },
  groupsApi: { list: vi.fn().mockResolvedValue({ numPages: 1, page: { objectList: [] } }) },
  usersApi: { list: vi.fn().mockResolvedValue([]) },
  flowsApi: { list: flowsApiList, get: flowsApiGet },
}))

vi.mock('../lib/pluginHealth', () => ({
  isAtlasApisAvailable: vi.fn().mockResolvedValue(true),
}))

vi.mock('../lib/apiSearch', () => ({
  endpointsApi: {
    search: vi.fn().mockResolvedValue({
      count: 1,
      numPages: 1,
      perPage: 20,
      page: {
        number: 1,
        objectList: [
          { endpoint: { id: 'e1', method: 'POST', path: '/foo', summary: 'Creates a foo' }, api: { ref: 'api:a', name: 'a', title: 'A' } },
        ],
      },
    }),
  },
  operationsApi: {
    search: vi.fn().mockResolvedValue({
      count: 1,
      numPages: 1,
      perPage: 20,
      page: {
        number: 1,
        objectList: [
          { operation: { id: 'o1', channelAddress: 'orders.created', direction: 'send', summary: 'Emitted when an order is created' }, api: { ref: 'api:a', name: 'a', title: 'A' } },
        ],
      },
    }),
  },
}))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function renderModal(props: Partial<ComponentProps<typeof FlowStepModal>> = {}) {
  return render(
    <ThemeProvider theme="light">
      <FlowEntityCatalogProvider>
        <FlowStepModal
          open
          steps={[]}
          step={null}
          onClose={() => {}}
          onSave={() => {}}
          {...props}
        />
      </FlowEntityCatalogProvider>
    </ThemeProvider>,
  )
}

function pickKind(name: RegExp) {
  fireEvent.click(screen.getByRole('button', { name }))
}

function titleInput() {
  return screen.getByPlaceholderText('Title (optional)') as HTMLInputElement
}

function summaryInput() {
  return screen.getByPlaceholderText('Summary (optional)') as HTMLTextAreaElement
}

describe('FlowStepModal Title/Summary/Id fields', () => {
  it('keeps the free-text Title/Summary fields for Step and External kinds', () => {
    renderModal()
    pickKind(/^Step/)

    expect(titleInput()).toBeTruthy()
    expect(summaryInput()).toBeTruthy()
  })

  it('drops the Title/Summary fields entirely for an entity-backed kind (Component)', () => {
    renderModal()
    pickKind(/^Component/)

    expect(screen.queryByPlaceholderText('Title (optional)')).toBeNull()
    expect(screen.queryByPlaceholderText('Summary (optional)')).toBeNull()
  })

  it('never offers an id field, for any kind', () => {
    renderModal()
    pickKind(/^Step/)

    expect(screen.queryByPlaceholderText('step-id')).toBeNull()
    expect(screen.queryByText('Id')).toBeNull()
  })

  it('saves an entity-backed step with no title/summary even if the step previously carried them (pre-existing data)', () => {
    const onSave = vi.fn()
    const staleStep: FlowStep = { id: 'n1', title: 'Stale title', summary: 'Stale summary', entity_ref: 'component:booking-web' }
    renderModal({ step: staleStep, onSave })

    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ title: undefined, summary: undefined, entity_ref: 'component:booking-web' }),
      'n1',
    )
  })
})

describe('FlowStepModal "Add Step" picker tile colors', () => {
  it('renders twelve tiles, six full rows, with no two adjacent tiles (same row or column) sharing a border color', () => {
    renderModal()

    // Before any kind is picked, the dialog's buttons are the 12 kind tiles
    // (each carrying `aria-disabled`, unlike the Dialog's own close button)
    // plus the Dialog's close button — filtered out below. Tile order matches
    // `KIND_TILES`, which is also DOM/grid order for a `repeat(2, 1fr)` grid
    // (row-major auto-placement).
    const tiles = screen.getAllByRole('button').filter((button) => button.hasAttribute('aria-disabled'))
    expect(tiles).toHaveLength(12)
    const borders = tiles.map((tile) => tile.getAttribute('style')?.match(/border: 2px solid ([^;]+);/)?.[1])
    expect(borders.every((border) => Boolean(border))).toBe(true)

    for (let index = 0; index < borders.length; index += 1) {
      // Horizontal neighbor: the other tile in the same row (indices swap by 1 within a pair).
      const rowPartner = index % 2 === 0 ? index + 1 : index - 1
      if (rowPartner < borders.length) expect(borders[index]).not.toBe(borders[rowPartner])
      // Vertical neighbor: same column, next row down (two tiles per row).
      const columnPartner = index + 2
      if (columnPartner < borders.length) expect(borders[index]).not.toBe(borders[columnPartner])
    }
  })
})

describe('FlowStepModal drops Title/Summary for API Call/Event too — their card renders text derived from the picked Endpoint/Operation snapshot itself, not typed text', () => {
  it('offers no Title/Summary fields for API Call', () => {
    renderModal()
    pickKind(/^API Call/)

    expect(screen.queryByPlaceholderText('Title (optional)')).toBeNull()
    expect(screen.queryByPlaceholderText('Summary (optional)')).toBeNull()
  })

  it('offers no Title/Summary fields for Event', () => {
    renderModal()
    pickKind(/^Event/)

    expect(screen.queryByPlaceholderText('Title (optional)')).toBeNull()
    expect(screen.queryByPlaceholderText('Summary (optional)')).toBeNull()
  })

  it('saves an API Call step with no title/summary once an Endpoint is picked', async () => {
    const onSave = vi.fn()
    renderModal({ onSave })
    pickKind(/^API Call/)

    fireEvent.click(await screen.findByText('Search endpoints...'))
    fireEvent.click(await screen.findByText('POST /foo'))
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        title: undefined,
        summary: undefined,
        // The picked Endpoint's own summary is snapshotted onto query_ref itself
        // not the step's (now-removed) summary field.
        query_ref: expect.objectContaining({ method: 'POST', path: '/foo', summary: 'Creates a foo' }),
      }),
      null,
    )
  })

  it('saves an Event step with no title/summary once an Operation is picked', async () => {
    const onSave = vi.fn()
    renderModal({ onSave })
    pickKind(/^Event/)

    fireEvent.click(await screen.findByText('Search operations...'))
    fireEvent.click(await screen.findByText('orders.created'))
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        title: undefined,
        summary: undefined,
        event_ref: expect.objectContaining({ channel: 'orders.created', summary: 'Emitted when an order is created' }),
      }),
      null,
    )
  })
})

describe('FlowStepModal event direction/channel drift warning + refresh', () => {
  const eventStep: FlowStep = { id: 'e1', title: 'Node title', event_ref: { api: 'api:a', operation: 'o1', direction: 'send', channel: 'orders.created' } }
  const drifted = { status: 'active' as const, deprecated: false, live: { direction: 'receive', channel_address: 'orders.events' } }

  it('shows the warning and refresh control next to the Operation select when refStatus indicates drift', () => {
    renderModal({ step: eventStep, refStatus: drifted })

    expect(screen.getByLabelText(/Live operation is now receive orders\.events/)).toBeTruthy()
    expect(screen.getByLabelText('Refresh from live operation')).toBeTruthy()
  })

  it('shows neither the warning nor the refresh control when the stored event_ref still matches', () => {
    renderModal({ step: eventStep, refStatus: { status: 'active', deprecated: false } })

    expect(screen.queryByLabelText(/Live operation is now/)).toBeNull()
    expect(screen.queryByLabelText('Refresh from live operation')).toBeNull()
  })

  it('a normal open does not prefill: saving without touching the control keeps the stored event_ref', () => {
    const onSave = vi.fn()
    renderModal({ step: eventStep, refStatus: drifted, onSave })

    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ event_ref: eventStep.event_ref }), 'e1')
  })

  it('clicking the in-modal refresh control fills event_ref from live data, persisted only once Save is clicked', () => {
    const onSave = vi.fn()
    renderModal({ step: eventStep, refStatus: drifted, onSave })

    fireEvent.click(screen.getByLabelText('Refresh from live operation'))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ event_ref: { api: 'api:a', operation: 'o1', direction: 'receive', channel: 'orders.events' } }),
      'e1',
    )
  })

  it('Cancel after a refresh discards the prefilled state without calling onSave', () => {
    const onSave = vi.fn()
    const onClose = vi.fn()
    renderModal({ step: eventStep, refStatus: drifted, onSave, onClose })

    fireEvent.click(screen.getByLabelText('Refresh from live operation'))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onSave).not.toHaveBeenCalled()
    expect(onClose).toHaveBeenCalled()
  })

  it('an event_ref summary-only drift (no direction/channel change) still shows the warning and refresh, and refresh only updates summary', () => {
    const onSave = vi.fn()
    const summaryDrifted = { status: 'active' as const, deprecated: false, live: { summary: 'New summary' } }
    renderModal({ step: eventStep, refStatus: summaryDrifted, onSave })

    expect(screen.getByLabelText(/Live operation summary is now "New summary"/)).toBeTruthy()
    fireEvent.click(screen.getByLabelText('Refresh from live operation'))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ event_ref: { ...eventStep.event_ref, summary: 'New summary' } }),
      'e1',
    )
  })
})

describe('FlowStepModal query_ref summary drift warning + refresh', () => {
  const callStep: FlowStep = { id: 'c1', query_ref: { api: 'api:a', endpoint: 'e1', method: 'GET', path: '/foo', summary: 'Old summary' } }
  const drifted = { status: 'active' as const, deprecated: false, live: { summary: 'New summary' } }

  it('shows the warning and refresh control next to the Endpoint select when refStatus indicates a summary drift', () => {
    renderModal({ step: callStep, refStatus: drifted })

    expect(screen.getByLabelText(/Live endpoint summary is now "New summary"/)).toBeTruthy()
    expect(screen.getByLabelText('Refresh from live endpoint')).toBeTruthy()
  })

  it('shows neither the warning nor the refresh control when the stored query_ref summary still matches', () => {
    renderModal({ step: callStep, refStatus: { status: 'active', deprecated: false } })

    expect(screen.queryByLabelText(/Live endpoint summary is now/)).toBeNull()
    expect(screen.queryByLabelText('Refresh from live endpoint')).toBeNull()
  })

  it('a normal open does not prefill: saving without touching the control keeps the stored query_ref', () => {
    const onSave = vi.fn()
    renderModal({ step: callStep, refStatus: drifted, onSave })

    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ query_ref: callStep.query_ref }), 'c1')
  })

  it('clicking the in-modal refresh control fills query_ref.summary from live data, persisted only once Save is clicked', () => {
    const onSave = vi.fn()
    renderModal({ step: callStep, refStatus: drifted, onSave })

    fireEvent.click(screen.getByLabelText('Refresh from live endpoint'))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ query_ref: { ...callStep.query_ref, summary: 'New summary' } }),
      'c1',
    )
  })

})

describe('FlowStepModal Flow/Link node-type picker and edit modal', () => {
  it('adds a Flow step via the picker, storing the selected Flow\'s id as flow_ref and no title/summary', async () => {
    const onSave = vi.fn()
    renderModal({ onSave })
    pickKind(/^Flow/)

    expect(flowsApiList).toHaveBeenCalled()
    fireEvent.click(await screen.findByText('Search Flows...'))
    fireEvent.click(await screen.findByText('Checkout'))
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ flow_ref: 7, title: undefined, summary: undefined }),
      null,
    )
  })

  it('adds a Link step via the picker, storing the URL and any entered title/summary as link_url/title/summary', () => {
    const onSave = vi.fn()
    renderModal({ onSave })
    pickKind(/^Link/)

    fireEvent.change(titleInput(), { target: { value: 'Docs' } })
    fireEvent.change(screen.getByPlaceholderText('https://example.com'), { target: { value: 'https://example.com/docs' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ link_url: 'https://example.com/docs', title: 'Docs' }),
      null,
    )
  })

  it('shows a validation message for Link until a well-formed http(s) URL is entered, and disables Add until then', () => {
    renderModal()
    pickKind(/^Link/)

    expect(screen.getByText('Enter a valid http(s) URL')).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Add' }) as HTMLButtonElement).disabled).toBe(true)

    fireEvent.change(screen.getByPlaceholderText('https://example.com'), { target: { value: 'javascript:alert(1)' } })
    expect(screen.getByText('Enter a valid http(s) URL')).toBeTruthy()

    fireEvent.change(screen.getByPlaceholderText('https://example.com'), { target: { value: 'https://example.com' } })
    expect(screen.queryByText('Enter a valid http(s) URL')).toBeNull()
    expect((screen.getByRole('button', { name: 'Add' }) as HTMLButtonElement).disabled).toBe(false)
  })

  it('clearing a freshly-picked Flow reference reverts the node to the plain Step type', async () => {
    renderModal()
    pickKind(/^Flow/)

    fireEvent.click(await screen.findByText('Search Flows...'))
    fireEvent.click(await screen.findByText('Checkout'))
    fireEvent.click(screen.getByRole('button', { name: 'Clear' }))

    // Step-only fields now render in place of the Flow lookup (clearing a
    // Flow reference).
    expect(screen.getByText('Type label')).toBeTruthy()
    expect(screen.queryByPlaceholderText('Search Flows...')).toBeNull()
  })

  it('shows the same stale-reference warning inside the modal as the canvas card, once the Flow is confirmed gone', async () => {
    const flowStep: FlowStep = { id: 'f1', flow_ref: 999 }
    renderModal({ step: flowStep })

    expect(await screen.findByLabelText('This Flow no longer exists.')).toBeTruthy()
  })

  it('clearing an existing Flow step\'s reference reverts it to a plain Step on save', () => {
    const onSave = vi.fn()
    const flowStep: FlowStep = { id: 'f1', flow_ref: 7 }
    renderModal({ step: flowStep, onSave })

    fireEvent.click(screen.getByRole('button', { name: 'Clear' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ flow_ref: undefined, entity_ref: undefined, external_label: undefined }),
      'f1',
    )
  })
})
