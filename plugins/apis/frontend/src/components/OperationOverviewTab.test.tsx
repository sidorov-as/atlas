// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { OperationOverviewTab } from './OperationOverviewTab'
import { makeApi, makeOperation, makeOperationMessage } from '../testFixtures'

afterEach(() => cleanup())

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

vi.mock('frontend/lib/entities', () => ({
  kindToPath: { system: '/systems', component: '/components', group: '/teams', api: '/apis' },
}))

vi.mock('frontend/lib/SessionContext', () => ({
  useSession: () => ({ session: { isAuthenticated: true, user: null }, isLoading: false, login: vi.fn(), logout: vi.fn() }),
}))

vi.mock('./OperationConsumersGraph', () => ({
  OperationConsumersGraph: () => <div>consumers graph</div>,
}))

function renderTab(overrides: Parameters<typeof makeOperation>[0] = {}, apiOverrides: Parameters<typeof makeApi>[0] = {}) {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <OperationOverviewTab
          operation={makeOperation(overrides)}
          api={makeApi(apiOverrides)}
          consumers={null}
          consumersLoading={false}
          consumersError={null}
          onRetryConsumers={vi.fn()}
          onViewLinkedServices={vi.fn()}
          linkedServicesTotal={0}
        />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('OperationOverviewTab', () => {
  it('shows the documentation card, even with no description', () => {
    renderTab({ description: '' })
    expect(screen.getByText('Documentation')).toBeDefined()
    expect(screen.getByText('No documentation')).toBeDefined()
  })

  it('shows the channel address, protocol, and direction', () => {
    renderTab({ channelAddress: 'booking.created', channelProtocol: 'kafka', direction: 'send' })
    expect(screen.getByText('Channel')).toBeDefined()
    expect(screen.getByText('booking.created')).toBeDefined()
    expect(screen.getByText('kafka')).toBeDefined()
  })

  it('omits the messages section when there are no messages', () => {
    renderTab({ messages: [] })
    expect(screen.queryByText(/^Message/)).toBeNull()
  })

  it('shows a messages section when messages exist', () => {
    renderTab({ messages: [makeOperationMessage({ summary: 'Fired on creation' })] })
    expect(screen.getByText('Message')).toBeDefined()
    expect(screen.getByText('BookingCreated')).toBeDefined()
  })

  it('shows an external docs link when externalDocs is present', () => {
    renderTab({ externalDocs: { description: 'Event catalog', url: 'https://docs.example.com/events' } })
    expect(screen.getByText('External docs')).toBeDefined()
    const link = screen.getByText('Event catalog').closest('a')
    expect(link?.getAttribute('href')).toBe('https://docs.example.com/events')
  })

  it('omits the external docs link when externalDocs is absent', () => {
    renderTab({ externalDocs: null })
    expect(screen.queryByText('External docs')).toBeNull()
  })

  it("shows the parent API's owner and system in the Details card", () => {
    renderTab()
    expect(screen.getByText('Owner')).toBeDefined()
    expect(screen.getByText('System')).toBeDefined()
    expect(screen.getByText('platform')).toBeDefined()
    expect(screen.getByText('core')).toBeDefined()
  })

  it('does not show a bottom Linked services section', () => {
    renderTab({}, {})
    expect(screen.queryByText('Linked services')).toBeNull()
    expect(screen.queryByText('No services are linked to this operation yet')).toBeNull()
  })

  it('omits the "View all" link next to the graph header when no services are linked', () => {
    renderTab({}, {})
    expect(screen.queryByText(/^View all/)).toBeNull()
  })

  it('links to the Linked Services tab from the "View all" link when services are linked', () => {
    render(
      <ThemeProvider theme="light">
        <MemoryRouter>
          <OperationOverviewTab
            operation={makeOperation()}
            api={makeApi()}
            consumers={null}
            consumersLoading={false}
            consumersError={null}
            onRetryConsumers={vi.fn()}
            onViewLinkedServices={vi.fn()}
            linkedServicesTotal={1}
          />
        </MemoryRouter>
      </ThemeProvider>,
    )
    expect(screen.getByText('View all 1 service')).toBeDefined()
  })

  it('groups Channel and Details into a row, ordered after Documentation and before Message, inside the two-column grid', () => {
    const { container } = renderTab({ messages: [makeOperationMessage()] })

    const grid = container.querySelector('.operation-overview-grid')
    expect(grid).not.toBeNull()
    // Left column: Documentation -> Channel/Details row -> Message. Right column: the graph.
    expect(grid!.contains(screen.getByText('Documentation'))).toBe(true)
    expect(grid!.contains(screen.getByText('Channel'))).toBe(true)
    expect(grid!.contains(screen.getByText('Message'))).toBe(true)
    expect(grid!.contains(screen.getByText('Details'))).toBe(true)
    expect(grid!.contains(screen.getByText('consumers graph'))).toBe(true)

    const row = container.querySelector('.operation-channel-details-row')
    expect(row).not.toBeNull()
    expect(row!.contains(screen.getByText('Channel'))).toBe(true)
    expect(row!.contains(screen.getByText('Details'))).toBe(true)
    expect(row!.contains(screen.getByText('Message'))).toBe(false)

    // Message comes after the row in DOM order.
    const position = row!.compareDocumentPosition(screen.getByText('Message'))
    // eslint-disable-next-line no-bitwise
    expect(Boolean(position & Node.DOCUMENT_POSITION_FOLLOWING)).toBe(true)
  })
})
