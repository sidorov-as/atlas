// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LinkOperationServiceDialog } from './LinkOperationServiceDialog'
import { componentsApi } from 'frontend/lib/entities'
import { operationServicesApi } from '../lib/entities'
import { makeOperation, makeServiceSummary } from '../testFixtures'
import type { ComponentEntity } from 'frontend/lib/types'

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
vi.stubGlobal('matchMedia', (query: string) => ({
  matches: false, media: query, onchange: null,
  addListener: () => {}, removeListener: () => {},
  addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
}))

vi.mock('frontend/lib/entities', () => ({
  componentsApi: { list: vi.fn() },
}))

vi.mock('../lib/entities', () => ({
  operationServicesApi: { link: vi.fn(), linkedServiceRolePairs: vi.fn() },
}))

function makeComponent(overrides: Partial<ComponentEntity> = {}): ComponentEntity {
  return {
    id: 'service-1',
    apiVersion: 'atlas/v1alpha1',
    kind: 'Component',
    metadata: { name: 'billing-service', title: '', description: '', documentation: '', labels: {}, tags: [], tagColors: {}, links: [] },
    spec: {
      type: 'service', lifecycle: 'production', owner: 'group:platform', ownerId: 'group-1',
      system: 'system:core', systemId: 'system-1', providesApis: [], consumesApis: [], dependsOn: [],
    },
    status: 'active',
    ingestedFrom: null,
    blockedBy: null,
    blockedByReason: null,
    capabilities: [],
    ...overrides,
  }
}

function makeProviderComponent(): ComponentEntity {
  return makeComponent({ id: 'provider-1', metadata: { ...makeComponent().metadata, name: 'booking-service' } })
}

function renderDialog(props: Partial<Parameters<typeof LinkOperationServiceDialog>[0]> & { linked?: string[] } = {}) {
  const { linked = [], ...dialogProps } = props
  vi.mocked(operationServicesApi.linkedServiceRolePairs).mockResolvedValue(linked)
  const onClose = vi.fn()
  const onLinked = vi.fn()
  render(
    <ThemeProvider theme="light">
      <LinkOperationServiceDialog
        open
        onClose={onClose}
        operation={makeOperation()}
        onLinked={onLinked}
        {...dialogProps}
      />
    </ThemeProvider>,
  )
  return { onClose, onLinked }
}

describe('LinkOperationServiceDialog', () => {
  it('excludes the operation\'s own document-owner Service from the picker', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue({
      count: 2, numPages: 1, perPage: 100, page: { number: 1, objectList: [makeComponent(), makeProviderComponent()] },
    })
    renderDialog({
      operation: makeOperation({ provider: { service: makeServiceSummary({ id: 'provider-1' }), role: 'publisher' } }),
    })

    fireEvent.click(await screen.findByText('Select a service…'))
    await waitFor(() => expect(screen.getByText('billing-service')).toBeDefined())
    expect(screen.queryByText('booking-service')).toBeNull()
  })

  it('shows an "Already linked" marker for a service already linked with the selected role', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue({
      count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [makeComponent()] },
    })
    renderDialog({ linked: ['service-1:subscriber'] })

    fireEvent.click(await screen.findByText('Select a service…'))
    await waitFor(() => expect(screen.getByText('Already linked')).toBeDefined())
  })

  it('does not mark a service as already linked for a role it is not linked with', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue({
      count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [makeComponent()] },
    })
    // Linked as subscriber, but the dialog defaults to the publisher/subscriber
    // picker's own default role — publisher is not yet linked.
    renderDialog({ linked: ['service-1:subscriber'] })

    fireEvent.click(screen.getByText('Publisher'))
    fireEvent.click(await screen.findByText('Select a service…'))
    await waitFor(() => expect(screen.getByText('billing-service')).toBeDefined())
    expect(screen.queryByText('Already linked')).toBeNull()
  })

  it('defaults the role picker to subscriber', () => {
    renderDialog()
    const subscriberOption = screen.getByText('Subscriber').closest('label')
    expect(subscriberOption?.querySelector('input')?.checked).toBe(true)
  })

  it('submits the link with the selected role and calls onLinked/onClose on success', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue({
      count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [makeComponent()] },
    })
    vi.mocked(operationServicesApi.link).mockResolvedValue({
      id: 'usage-1',
      service: makeServiceSummary(),
      role: 'publisher',
      linkedAt: '2026-01-01T00:00:00Z',
    })
    const { onClose, onLinked } = renderDialog()

    fireEvent.click(screen.getByText('Publisher'))
    fireEvent.click(await screen.findByText('Select a service…'))
    fireEvent.click(await screen.findByText('billing-service'))
    fireEvent.click(screen.getByText('Link'))

    await waitFor(() => expect(operationServicesApi.link).toHaveBeenCalledWith('operation-1', 'service-1', 'publisher'))
    await waitFor(() => expect(onLinked).toHaveBeenCalled())
    expect(onClose).toHaveBeenCalled()
  })

  it('disables the Link button until a service is selected', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue({
      count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [makeComponent()] },
    })
    renderDialog()

    const button = screen.getByText('Link').closest('button')
    expect(button?.hasAttribute('disabled')).toBe(true)
  })

  it('disables the Link button and shows an explanation when switching role lands on an already-linked pair', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue({
      count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [makeComponent()] },
    })
    // Only linked as publisher — selecting it while the default role
    // (subscriber) is active is allowed (the option isn't disabled), then
    // switching the role picker to publisher lands on the already-linked pair.
    renderDialog({ linked: ['service-1:publisher'] })

    fireEvent.click(await screen.findByText('Select a service…'))
    fireEvent.click(await screen.findByText('billing-service'))
    fireEvent.click(screen.getByText('Publisher'))

    await waitFor(() => expect(screen.getByText('This service is already linked with this role.')).toBeDefined())
    const button = screen.getByText('Link').closest('button')
    expect(button?.hasAttribute('disabled')).toBe(true)
  })

  it('disables a service linked beyond the first 50 links, using the exact server check', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue({
      count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [makeComponent()] },
    })
    const manyLinks = Array.from({ length: 60 }, (_, index) => `other-${index}:subscriber`)
    renderDialog({ linked: [...manyLinks, 'service-1:subscriber'] })

    fireEvent.click(await screen.findByText('Select a service…'))
    await waitFor(() => expect(screen.getByText('Already linked')).toBeDefined())
  })
})
