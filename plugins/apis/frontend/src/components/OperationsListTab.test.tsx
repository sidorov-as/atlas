// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { OperationsListTab } from './OperationsListTab'
import { operationServicesApi, operationsApi } from '../lib/entities'
import { makeOperation, makeOperationConsumers, makeServiceSummary } from '../testFixtures'

const goToPage2 = () => fireEvent.click(document.querySelector('[data-qa="pagination-page-2"]')!)

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

vi.mock('../lib/entities', () => ({
  operationsApi: { list: vi.fn() },
  operationServicesApi: { consumers: vi.fn() },
}))

function renderTab(apiId = 'api-1') {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <OperationsListTab apiId={apiId} />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('OperationsListTab', () => {
  it('groups two operations sharing a channel address into one section, not two rows', async () => {
    vi.mocked(operationsApi.list).mockResolvedValue([
      makeOperation({ id: 'operation-1', channelAddress: 'booking.created', direction: 'send' }),
      makeOperation({ id: 'operation-2', channelAddress: 'booking.created', direction: 'receive' }),
    ])
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderTab()

    await waitFor(() => expect(screen.getAllByText('booking.created')).toHaveLength(1))
    expect(screen.getByText('Send')).toBeDefined()
    expect(screen.getByText('Receive')).toBeDefined()
  })

  it('renders a separate section per distinct channel address', async () => {
    vi.mocked(operationsApi.list).mockResolvedValue([
      makeOperation({ id: 'operation-1', channelAddress: 'booking.created' }),
      makeOperation({ id: 'operation-2', channelAddress: 'payment.settled', operationKey: 'onPaymentSettled' }),
    ])
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderTab()

    await waitFor(() => expect(screen.getByText('booking.created')).toBeDefined())
    expect(screen.getByText('payment.settled')).toBeDefined()
  })

  it('shows a publisher/subscriber count summary per channel section', async () => {
    vi.mocked(operationsApi.list).mockResolvedValue([makeOperation({ channelAddress: 'booking.created' })])
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(
      makeOperationConsumers([
        { service: makeServiceSummary({ id: 'service-1' }), role: 'publisher' },
        { service: makeServiceSummary({ id: 'service-2' }), role: 'subscriber' },
        { service: makeServiceSummary({ id: 'service-3' }), role: 'subscriber' },
      ]),
    )

    renderTab()

    await waitFor(() => expect(screen.getByText('1 publisher, 2 subscribers')).toBeDefined())
  })

  it('defaults to the active-operations list', async () => {
    vi.mocked(operationsApi.list).mockResolvedValue([])
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderTab()

    await waitFor(() => expect(operationsApi.list).toHaveBeenCalledWith('api-1', expect.objectContaining({ status: 'active' })))
  })

  it('switching to "Removed operations" refetches with status=removed', async () => {
    vi.mocked(operationsApi.list).mockResolvedValue([])
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderTab()
    await waitFor(() => expect(operationsApi.list).toHaveBeenCalled())

    fireEvent.click(screen.getByText('Removed operations'))

    await waitFor(() =>
      expect(operationsApi.list).toHaveBeenLastCalledWith('api-1', expect.objectContaining({ status: 'removed' })),
    )
  })

  it('searching calls the list API with the search term', async () => {
    vi.mocked(operationsApi.list).mockResolvedValue([])
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderTab()
    await waitFor(() => expect(operationsApi.list).toHaveBeenCalled())

    fireEvent.change(screen.getByPlaceholderText('Search channel, summary, operation ID…'), { target: { value: 'booking' } })

    await waitFor(() =>
      expect(operationsApi.list).toHaveBeenLastCalledWith('api-1', expect.objectContaining({ search: 'booking' })),
    )
  })

  it('shows a removed-operation indicator on a removed row within its channel group', async () => {
    vi.mocked(operationsApi.list).mockResolvedValue([makeOperation({ status: 'removed' })])
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderTab()

    await waitFor(() => expect(screen.getByText('Removed')).toBeDefined())
  })

  it('shows an empty state distinguishing no operations from no removed operations', async () => {
    vi.mocked(operationsApi.list).mockResolvedValue([])
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderTab()

    await waitFor(() => expect(screen.getByText('No operations')).toBeDefined())
  })

  it('shows a channel that straddles a page boundary on both pages', async () => {
    const operations = Array.from({ length: 16 }, (_, index) =>
      makeOperation({
        id: `operation-${index}`,
        channelAddress: index < 14 ? `channel.${index}` : 'shared.channel',
        operationKey: `op-${index}`,
        summary: `Operation ${index}`,
      }),
    )
    vi.mocked(operationsApi.list).mockResolvedValue(operations)
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderTab()
    await waitFor(() => expect(screen.getByText('Operation 14')).toBeDefined())
    expect(screen.queryByText('Operation 15')).toBeNull()
    expect(screen.getByText('shared.channel')).toBeDefined()

    goToPage2()

    await waitFor(() => expect(screen.getByText('Operation 15')).toBeDefined())
    expect(screen.getByText('shared.channel')).toBeDefined()
  })

  it('takes the publisher/subscriber summary from the role totals, not the returned page', async () => {
    vi.mocked(operationsApi.list).mockResolvedValue([makeOperation({ channelAddress: 'booking.created' })])
    vi.mocked(operationServicesApi.consumers).mockResolvedValue({
      ...makeOperationConsumers([{ service: makeServiceSummary({ id: 'service-1' }), role: 'publisher' }]),
      count: 70,
      publisherCount: 60,
      subscriberCount: 10,
    })

    renderTab()

    await waitFor(() => expect(screen.getByText('60 publishers, 10 subscribers')).toBeDefined())
  })
})
